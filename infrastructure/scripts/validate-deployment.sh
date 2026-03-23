#!/bin/bash

# デプロイメント検証スクリプト

set -e

ENVIRONMENT=${1:-development}
STACK_NAME="PeGptEcsStack-${ENVIRONMENT}"

echo "Validating deployment for environment: ${ENVIRONMENT}"

# スタックの存在確認
echo "Checking if stack exists..."
if ! aws cloudformation describe-stacks --stack-name ${STACK_NAME} >/dev/null 2>&1; then
  echo "Error: Stack ${STACK_NAME} does not exist"
  exit 1
fi

# スタックの状態確認
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].StackStatus' --output text)
echo "Stack status: ${STACK_STATUS}"

if [[ "${STACK_STATUS}" != "CREATE_COMPLETE" && "${STACK_STATUS}" != "UPDATE_COMPLETE" ]]; then
  echo "Error: Stack is not in a healthy state"
  exit 1
fi

# ALBのDNS名を取得
ALB_DNS=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' --output text)

if [[ -z "${ALB_DNS}" ]]; then
  echo "Error: Could not retrieve ALB DNS name"
  exit 1
fi

echo "ALB DNS: ${ALB_DNS}"

# ヘルスチェック
echo "Performing health check..."
MAX_ATTEMPTS=30
ATTEMPT=1

while [[ ${ATTEMPT} -le ${MAX_ATTEMPTS} ]]; do
  echo "Attempt ${ATTEMPT}/${MAX_ATTEMPTS}: Checking http://${ALB_DNS}"
  
  if curl -f -s "http://${ALB_DNS}" >/dev/null; then
    echo "✅ Health check passed!"
    break
  fi
  
  if [[ ${ATTEMPT} -eq ${MAX_ATTEMPTS} ]]; then
    echo "❌ Health check failed after ${MAX_ATTEMPTS} attempts"
    exit 1
  fi
  
  echo "Waiting 10 seconds before next attempt..."
  sleep 10
  ((ATTEMPT++))
done

# ECSサービスの状態確認
echo "Checking ECS service status..."
CLUSTER_NAME=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs[?OutputKey==`ClusterName`].OutputValue' --output text)

if [[ -n "${CLUSTER_NAME}" ]]; then
  SERVICE_STATUS=$(aws ecs describe-services --cluster ${CLUSTER_NAME} --services pe-gpt-service --query 'services[0].status' --output text 2>/dev/null || echo "NOT_FOUND")
  echo "ECS Service status: ${SERVICE_STATUS}"
  
  if [[ "${SERVICE_STATUS}" == "ACTIVE" ]]; then
    RUNNING_COUNT=$(aws ecs describe-services --cluster ${CLUSTER_NAME} --services pe-gpt-service --query 'services[0].runningCount' --output text)
    DESIRED_COUNT=$(aws ecs describe-services --cluster ${CLUSTER_NAME} --services pe-gpt-service --query 'services[0].desiredCount' --output text)
    echo "Running tasks: ${RUNNING_COUNT}/${DESIRED_COUNT}"
  fi
fi

echo "✅ Deployment validation completed successfully!"
echo "Application is accessible at: http://${ALB_DNS}"