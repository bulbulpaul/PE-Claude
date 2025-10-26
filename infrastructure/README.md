# PE-GPT ECS Infrastructure

This directory contains the AWS CDK infrastructure code for deploying PE-GPT on Amazon ECS with Fargate.

## Prerequisites

- Node.js 18.x or later
- AWS CLI configured with appropriate permissions
- Docker installed (for building and pushing container images)

## Project Structure

```
infrastructure/
├── bin/                    # CDK app entry point
├── lib/                    # CDK stack definitions
├── scripts/                # Deployment and utility scripts
├── test/                   # Unit tests for CDK stacks
├── cdk.json               # CDK configuration
├── package.json           # Node.js dependencies
└── tsconfig.json          # TypeScript configuration
```

## Setup

1. Install dependencies:
   ```bash
   cd infrastructure
   npm install
   ```

2. Build the TypeScript code:
   ```bash
   npm run build
   ```

3. Bootstrap CDK (first time only):
   ```bash
   npx cdk bootstrap
   ```

## Deployment

### Quick Deployment
Use the deployment script for a complete deployment:
```bash
./scripts/deploy.sh
```

### Manual Deployment Steps

1. **Deploy Infrastructure:**
   ```bash
   npx cdk deploy
   ```

2. **Build and Push Docker Image:**
   ```bash
   ./scripts/build-and-push.sh [IMAGE_TAG]
   ```

3. **Update ECS Service** (after infrastructure is deployed):
   The ECS service will automatically use the latest image from ECR.

## Available Scripts

- `npm run build` - Compile TypeScript
- `npm run watch` - Watch for changes and compile
- `npm run test` - Run unit tests
- `npm run cdk` - Run CDK CLI commands
- `./scripts/deploy.sh` - Complete deployment
- `./scripts/destroy.sh` - Destroy the stack
- `./scripts/build-and-push.sh` - Build and push Docker image

## Environment Variables

The following environment variables can be set:

- `CDK_DEFAULT_ACCOUNT` - AWS account ID
- `CDK_DEFAULT_REGION` - AWS region (default: us-east-1)
- `AWS_DEFAULT_REGION` - AWS region for CLI operations

## Architecture

The infrastructure creates:

- VPC with public and private subnets
- ECR repository for container images
- ECS Fargate cluster and service
- Application Load Balancer
- IAM roles and security groups
- CloudWatch log groups

## Monitoring

After deployment, you can monitor the application through:

- AWS ECS Console - Service and task status
- CloudWatch Logs - Application logs
- ALB Target Groups - Health check status

## Cleanup

To destroy all resources:
```bash
./scripts/destroy.sh
```

**Warning:** This will permanently delete all resources and data.