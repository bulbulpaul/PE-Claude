#!/bin/bash

# PE-GPT Docker イメージのビルドとECRへのプッシュスクリプト

set -e

# 設定
REGION=${AWS_DEFAULT_REGION:-us-east-1}
REPOSITORY_NAME="pe-gpt"
IMAGE_TAG=${1:-latest}

# AWSアカウントIDを取得
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# ECRリポジトリURIを構築
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPOSITORY_NAME}"

echo "Building and pushing Docker image to ECR..."
echo "Repository: ${ECR_URI}"
echo "Tag: ${IMAGE_TAG}"

# ECRにログイン
echo "Logging in to ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Dockerイメージをビルド（ARM64アーキテクチャ用 - Graviton）
echo "Building Docker image for ARM64 architecture..."
docker build --platform linux/arm64 -t ${REPOSITORY_NAME}:${IMAGE_TAG} -f ../../Dockerfile ../..

# イメージにECRタグを付与
docker tag ${REPOSITORY_NAME}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}

# ECRにプッシュ
echo "Pushing image to ECR..."
docker push ${ECR_URI}:${IMAGE_TAG}

echo "Successfully pushed ${ECR_URI}:${IMAGE_TAG}"