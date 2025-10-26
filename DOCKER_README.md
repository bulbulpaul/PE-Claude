# PE-GPT Docker Containerization

This document provides instructions for building and running the PE-GPT application in a Docker container.

## Files Overview

### Core Docker Files

- **Dockerfile**: Multi-stage Docker build configuration for PE-GPT application
- **.dockerignore**: Optimizes build context by excluding unnecessary files
- **docker-entrypoint.sh**: Container startup script with health checks
- **docker-build.sh**: Convenience script for building the Docker image

## Building the Docker Image

### Prerequisites

- Docker installed and running
- Sufficient disk space (approximately 2GB for the image)

### Build Commands

#### Using the build script (recommended):
```bash
./docker-build.sh
```

#### Manual build:
```bash
docker build -t pe-gpt:latest .
```

#### Build with specific tag:
```bash
docker build -t pe-gpt:v1.0.0 .
```

## Running the Container

### Basic Run
```bash
docker run -p 8501:8501 pe-gpt:latest
```

### Run with Environment Variables
```bash
docker run -p 8501:8501 \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e BEDROCK_KB_ID=your-kb-id \
  pe-gpt:latest
```

### Run with AWS Credentials (for Bedrock access)
```bash
docker run -p 8501:8501 \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=your-access-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret-key \
  -e BEDROCK_KB_ID=your-kb-id \
  pe-gpt:latest
```

### Run in Background (Detached Mode)
```bash
docker run -d -p 8501:8501 \
  --name pe-gpt-app \
  -e AWS_DEFAULT_REGION=us-east-1 \
  pe-gpt:latest
```

## Environment Variables

### Required
- `AWS_DEFAULT_REGION`: AWS region (default: us-east-1)

### Optional
- `BEDROCK_KB_ID`: Bedrock Knowledge Base ID for enhanced functionality
- `BEDROCK_KB_REGION`: Bedrock region (default: same as AWS_DEFAULT_REGION)
- `BEDROCK_KB_MODE`: Operation mode (local/bedrock/hybrid, default: hybrid)
- `AWS_ACCESS_KEY_ID`: AWS access key for Bedrock access
- `AWS_SECRET_ACCESS_KEY`: AWS secret key for Bedrock access

### Streamlit Configuration (automatically set)
- `STREAMLIT_SERVER_HEADLESS=true`
- `STREAMLIT_SERVER_PORT=8501`
- `STREAMLIT_SERVER_ADDRESS=0.0.0.0`

## Health Checks

The container includes built-in health checks:

- **Endpoint**: `http://localhost:8501/_stcore/health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Start Period**: 60 seconds
- **Retries**: 3

### Manual Health Check
```bash
# Check if container is healthy
docker ps

# View health check logs
docker inspect --format='{{json .State.Health}}' container-name

# Manual health check
curl http://localhost:8501/_stcore/health
```

## Container Management

### View Running Containers
```bash
docker ps
```

### View Container Logs
```bash
docker logs pe-gpt-app
```

### Stop Container
```bash
docker stop pe-gpt-app
```

### Remove Container
```bash
docker rm pe-gpt-app
```

### Access Container Shell
```bash
docker exec -it pe-gpt-app /bin/bash
```

## Troubleshooting

### Common Issues

#### 1. Container Fails to Start
```bash
# Check container logs
docker logs container-name

# Common causes:
# - Missing required environment variables
# - Port 8501 already in use
# - Insufficient memory
```

#### 2. Application Not Accessible
```bash
# Verify port mapping
docker port container-name

# Check if application is running inside container
docker exec container-name curl http://localhost:8501/_stcore/health
```

#### 3. AWS/Bedrock Connection Issues
```bash
# Verify AWS credentials
docker exec container-name env | grep AWS

# Test AWS connectivity
docker exec container-name aws sts get-caller-identity
```

### Performance Optimization

#### Resource Limits
```bash
# Run with memory limit
docker run -p 8501:8501 --memory=2g pe-gpt:latest

# Run with CPU limit
docker run -p 8501:8501 --cpus=1.0 pe-gpt:latest
```

#### Volume Mounting for Development
```bash
# Mount source code for development
docker run -p 8501:8501 \
  -v $(pwd):/app \
  -e AWS_DEFAULT_REGION=us-east-1 \
  pe-gpt:latest
```

## Security Considerations

1. **Non-root User**: Container runs as non-root user 'app'
2. **Minimal Base Image**: Uses python:3.11-slim for reduced attack surface
3. **Environment Variables**: Sensitive data should be passed via environment variables
4. **Network Security**: Only exposes port 8501 for Streamlit

## Image Information

- **Base Image**: python:3.11-slim
- **Exposed Port**: 8501
- **Working Directory**: /app
- **User**: app (non-root)
- **Health Check**: Built-in Streamlit health endpoint

## Development Workflow

1. Make changes to application code
2. Build new Docker image: `./docker-build.sh`
3. Test locally: `docker run -p 8501:8501 pe-gpt:latest`
4. Tag for deployment: `docker tag pe-gpt:latest your-registry/pe-gpt:version`
5. Push to registry: `docker push your-registry/pe-gpt:version`

## Integration with ECS

This Docker image is designed to work with Amazon ECS. Key features:

- **Health Checks**: Compatible with ECS health check requirements
- **Graceful Shutdown**: Handles SIGTERM signals properly
- **Environment Variables**: Supports ECS task definition environment variables
- **Logging**: Outputs to stdout/stderr for CloudWatch integration
- **Non-root User**: Follows ECS security best practices