#!/bin/bash

# 環境別CDKデプロイメントスクリプト
# ECR スタックと ECS スタックを分離してデプロイ

set -e

# デフォルト値
ENVIRONMENT="development"
FORCE_DEPLOY=false
SKIP_ECR=false
SKIP_ECS=false
SKIP_IMAGE_BUILD=false

# 引数解析
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --force-deploy)
      FORCE_DEPLOY=true
      shift
      ;;
    --skip-ecr)
      SKIP_ECR=true
      shift
      ;;
    --skip-ecs)
      SKIP_ECS=true
      shift
      ;;
    --skip-image-build)
      SKIP_IMAGE_BUILD=true
      shift
      ;;
    --ecr-only)
      SKIP_ECS=true
      SKIP_IMAGE_BUILD=true
      shift
      ;;
    --ecs-only)
      SKIP_ECR=true
      SKIP_IMAGE_BUILD=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [-e|--environment ENV] [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  -e, --environment    Environment to deploy (development|staging|production)"
      echo "  --force-deploy       Force deployment without confirmation"
      echo "  --skip-ecr           Skip ECR stack deployment"
      echo "  --skip-ecs           Skip ECS stack deployment"
      echo "  --skip-image-build   Skip Docker image build and push"
      echo "  --ecr-only           Deploy only ECR stack (skip image build and ECS)"
      echo "  --ecs-only           Deploy only ECS stack (skip ECR and image build)"
      echo ""
      echo "Environment Variables (optional):"
      echo "  BEDROCK_KB_ID        Bedrock Knowledge Base ID"
      echo "  CERTIFICATE_ARN      ACM Certificate ARN for HTTPS (required for staging/production)"
      echo "  DOMAIN_NAME          Custom domain name (overrides configuration default)"
      echo ""
      echo "Deployment Flow:"
      echo "  1. ECR Stack (creates repository)"
      echo "  2. Docker Image Build & Push"
      echo "  3. ECS Stack (creates service)"
      echo ""
      echo "Examples:"
      echo "  # Full deployment (first time)"
      echo "  $0 -e development"
      echo ""
      echo "  # Update ECS only (after code changes)"
      echo "  $0 -e development --ecs-only"
      echo ""
      echo "  # Rebuild and push image, then update ECS"
      echo "  $0 -e development --skip-ecr"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

echo "=========================================="
echo "PE-GPT Deployment Script"
echo "=========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Skip ECR: ${SKIP_ECR}"
echo "Skip Image Build: ${SKIP_IMAGE_BUILD}"
echo "Skip ECS: ${SKIP_ECS}"
echo "=========================================="

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "${SCRIPT_DIR}")"
PROJECT_ROOT="$(dirname "${INFRA_DIR}")"

cd "${INFRA_DIR}"

# CDKのビルド
echo ""
echo "=== Building CDK project ==="
npm run build

# ECR スタックのデプロイ
ECR_STACK_NAME="PeGptEcrStack-${ENVIRONMENT}"
ECS_STACK_NAME="PeGptEcsStack-${ENVIRONMENT}"

if [[ "${SKIP_ECR}" != "true" ]]; then
  echo ""
  echo "=== Deploying ECR Stack ==="
  
  # ECR スタックの差分確認
  echo "Checking ECR stack diff..."
  npx cdk diff ${ECR_STACK_NAME} --context environment=${ENVIRONMENT} || true
  
  # 確認プロンプト
  if [[ "${FORCE_DEPLOY}" != "true" ]]; then
    read -p "Deploy ECR stack? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "ECR deployment skipped."
      SKIP_ECR=true
    fi
  fi
  
  if [[ "${SKIP_ECR}" != "true" ]]; then
    npx cdk deploy ${ECR_STACK_NAME} --context environment=${ENVIRONMENT} --require-approval never
    echo "ECR stack deployed successfully!"
  fi
fi

# ECR リポジトリ URI を取得
echo ""
echo "=== Getting ECR Repository URI ==="
ECR_URI=$(aws cloudformation describe-stacks \
  --stack-name ${ECR_STACK_NAME} \
  --query "Stacks[0].Outputs[?OutputKey=='RepositoryUri'].OutputValue" \
  --output text 2>/dev/null)

if [[ -z "${ECR_URI}" || "${ECR_URI}" == "None" ]]; then
  echo "Error: Could not get ECR Repository URI. Make sure ECR stack is deployed."
  echo "Run: $0 -e ${ENVIRONMENT} --ecr-only"
  exit 1
fi

echo "ECR Repository URI: ${ECR_URI}"

# Docker イメージのビルドとプッシュ
if [[ "${SKIP_IMAGE_BUILD}" != "true" ]]; then
  echo ""
  echo "=== Building and Pushing Docker Image ==="
  
  cd "${PROJECT_ROOT}"
  
  # ECR ログイン
  AWS_REGION=$(echo ${ECR_URI} | cut -d'.' -f4)
  AWS_ACCOUNT=$(echo ${ECR_URI} | cut -d'.' -f1)
  
  echo "Logging in to ECR..."
  aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com
  
  # Docker イメージのビルド
  echo "Building Docker image..."
  docker build -t pe-gpt:latest .
  
  # タグ付けとプッシュ
  echo "Tagging and pushing image..."
  docker tag pe-gpt:latest ${ECR_URI}:latest
  docker push ${ECR_URI}:latest
  
  echo "Docker image pushed successfully!"
  
  cd "${INFRA_DIR}"
fi

# ECS スタックのデプロイ
if [[ "${SKIP_ECS}" != "true" ]]; then
  echo ""
  echo "=== Deploying ECS Stack ==="
  
  # 環境変数の確認
  if [[ "${ENVIRONMENT}" == "production" && -z "${BEDROCK_KB_ID}" ]]; then
    echo "Warning: BEDROCK_KB_ID environment variable is not set for production"
  fi
  
  # ECS スタックの差分確認
  echo "Checking ECS stack diff..."
  npx cdk diff ${ECS_STACK_NAME} --context environment=${ENVIRONMENT} || true
  
  # 確認プロンプト
  if [[ "${FORCE_DEPLOY}" != "true" ]]; then
    read -p "Deploy ECS stack? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "ECS deployment cancelled."
      exit 0
    fi
  fi
  
  npx cdk deploy ${ECS_STACK_NAME} --context environment=${ENVIRONMENT} --require-approval never
  echo "ECS stack deployed successfully!"
fi

# デプロイメント結果の表示
echo ""
echo "=========================================="
echo "=== Deployment Summary ==="
echo "=========================================="
echo "Environment: ${ENVIRONMENT}"

# ECR 情報
echo ""
echo "--- ECR ---"
echo "Repository URI: ${ECR_URI}"

# ECS 情報
if [[ "${SKIP_ECS}" != "true" ]]; then
  echo ""
  echo "--- ECS & Application ---"
  
  # CloudFront URL
  CLOUDFRONT_URL=$(aws cloudformation describe-stacks --stack-name ${ECS_STACK_NAME} \
    --query "Stacks[0].Outputs[?OutputKey=='CloudFrontURL'].OutputValue" --output text 2>/dev/null || echo "Not available")
  echo "CloudFront URL: ${CLOUDFRONT_URL}"
  
  # ALB DNS
  ALB_DNS=$(aws cloudformation describe-stacks --stack-name ${ECS_STACK_NAME} \
    --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" --output text 2>/dev/null || echo "Not available")
  echo "Load Balancer DNS: ${ALB_DNS}"
  
  # Cognito
  USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name ${ECS_STACK_NAME} \
    --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" --output text 2>/dev/null || echo "Not available")
  echo "Cognito User Pool ID: ${USER_POOL_ID}"
  
  USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name ${ECS_STACK_NAME} \
    --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" --output text 2>/dev/null || echo "Not available")
  echo "Cognito Client ID: ${USER_POOL_CLIENT_ID}"
fi

echo ""
echo "=========================================="
echo "=== Next Steps ==="
echo "=========================================="
echo "1. Access the application: ${CLOUDFRONT_URL:-'Deploy ECS stack first'}"
echo "2. Create Cognito user: aws cognito-idp admin-create-user --user-pool-id ${USER_POOL_ID:-'<USER_POOL_ID>'} --username <email>"
echo ""
echo "For subsequent deployments:"
echo "  - Code changes only: $0 -e ${ENVIRONMENT} --skip-ecr"
echo "  - ECS config changes: $0 -e ${ENVIRONMENT} --ecs-only"
echo ""
