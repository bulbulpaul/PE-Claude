#!/bin/bash

# 環境別CDKデプロイメントスクリプト

set -e

# デフォルト値
ENVIRONMENT="development"
FORCE_DEPLOY=false

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
    -h|--help)
      echo "Usage: $0 [-e|--environment ENV] [--force-deploy]"
      echo "  -e, --environment    Environment to deploy (development|staging|production)"
      echo "  --force-deploy       Force deployment without confirmation"
      echo ""
      echo "Environment Variables (optional):"
      echo "  BEDROCK_KB_ID        Bedrock Knowledge Base ID"
      echo "  CERTIFICATE_ARN      ACM Certificate ARN for HTTPS (required for staging/production)"
      echo "  DOMAIN_NAME          Custom domain name (overrides configuration default)"
      echo "  CALLBACK_URLS        Comma-separated Cognito callback URLs"
      echo "  LOGOUT_URLS          Comma-separated Cognito logout URLs"
      echo ""
      echo "Example:"
      echo "  export CERTIFICATE_ARN=arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
      echo "  export DOMAIN_NAME=my-custom.domain.com"
      echo "  export CALLBACK_URLS=https://my-custom.domain.com/oauth2/idpresponse"
      echo "  export LOGOUT_URLS=https://my-custom.domain.com/"
      echo "  $0 -e production"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

echo "Deploying to environment: ${ENVIRONMENT}"

# 環境変数の確認
if [[ "${ENVIRONMENT}" == "production" && -z "${BEDROCK_KB_ID}" ]]; then
  echo "Warning: BEDROCK_KB_ID environment variable is not set for production"
fi

# HTTPS有効環境での証明書ARN確認
if [[ "${ENVIRONMENT}" == "staging" || "${ENVIRONMENT}" == "production" ]]; then
  if [[ -z "${CERTIFICATE_ARN}" ]]; then
    echo "Warning: CERTIFICATE_ARN environment variable is not set for ${ENVIRONMENT}"
    echo "  Set it with: export CERTIFICATE_ARN=arn:aws:acm:region:account:certificate/certificate-id"
  else
    echo "Using Certificate ARN: ${CERTIFICATE_ARN}"
  fi
  
  if [[ -z "${DOMAIN_NAME}" ]]; then
    echo "Info: DOMAIN_NAME environment variable is not set, using default from configuration"
  else
    echo "Using Domain Name: ${DOMAIN_NAME}"
  fi
  
  if [[ -n "${CALLBACK_URLS}" ]]; then
    echo "Using Callback URLs: ${CALLBACK_URLS}"
  fi
  
  if [[ -n "${LOGOUT_URLS}" ]]; then
    echo "Using Logout URLs: ${LOGOUT_URLS}"
  fi
fi

# CDKのビルド
echo "Building CDK project..."
npm run build

# CDKの差分確認
echo "Checking CDK diff..."
npx cdk diff --context environment=${ENVIRONMENT}

# 確認プロンプト（force-deployが指定されていない場合）
if [[ "${FORCE_DEPLOY}" != "true" ]]; then
  read -p "Do you want to proceed with deployment? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
  fi
fi

# デプロイメント実行
echo "Deploying CDK stack..."
npx cdk deploy --context environment=${ENVIRONMENT} --require-approval never

echo "Deployment completed successfully!"

# デプロイメント結果の表示
echo "Getting stack outputs..."
echo "Retrieving important deployment information..."

# スタック名を構築（実際のスタック名に合わせて調整が必要な場合があります）
STACK_NAME="PeGptEcsStack-${ENVIRONMENT}"

# 重要な出力値を取得して表示
echo ""
echo "=== Deployment Summary ==="
echo "Environment: ${ENVIRONMENT}"

# ALB DNS名を取得
ALB_DNS=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" --output text 2>/dev/null || echo "Not available")
echo "Load Balancer DNS: ${ALB_DNS}"

# Cognito関連の出力を取得
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" --output text 2>/dev/null || echo "Not available")
echo "Cognito User Pool ID: ${USER_POOL_ID}"

USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" --output text 2>/dev/null || echo "Not available")
echo "Cognito User Pool Client ID: ${USER_POOL_CLIENT_ID}"

USER_POOL_DOMAIN=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='UserPoolDomainUrl'].OutputValue" --output text 2>/dev/null || echo "Not available")
echo "Cognito Domain: ${USER_POOL_DOMAIN}"

if [[ "${ENVIRONMENT}" == "staging" || "${ENVIRONMENT}" == "production" ]]; then
  echo ""
  echo "HTTPS is enabled for this environment."
  if [[ -n "${CERTIFICATE_ARN}" ]]; then
    echo "Certificate ARN: ${CERTIFICATE_ARN}"
  fi
  if [[ -n "${DOMAIN_NAME}" ]]; then
    echo "Custom Domain: ${DOMAIN_NAME}"
  fi
fi

echo ""
echo "=== Next Steps ==="
echo "1. Verify the deployment by accessing the Load Balancer DNS"
if [[ "${ENVIRONMENT}" == "staging" || "${ENVIRONMENT}" == "production" ]]; then
  echo "2. Configure DNS records to point your domain to the Load Balancer"
  echo "3. Test the Cognito authentication flow"
fi
echo ""