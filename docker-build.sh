#!/bin/bash

# PE-GPT Docker Build Script
# This script builds the Docker image for PE-GPT application

set -e

# Configuration
IMAGE_NAME="pe-gpt"
IMAGE_TAG="latest"
DOCKERFILE="Dockerfile"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to build Docker image
build_image() {
    log "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"
    
    docker build \
        -t "${IMAGE_NAME}:${IMAGE_TAG}" \
        -f "${DOCKERFILE}" \
        .
    
    log "Docker image built successfully"
}

# Function to show image info
show_image_info() {
    log "Docker image information:"
    docker images "${IMAGE_NAME}:${IMAGE_TAG}"
    
    log "Image size and layers:"
    docker history "${IMAGE_NAME}:${IMAGE_TAG}"
}

# Function to test the image
test_image() {
    log "Testing Docker image..."
    
    # Run a quick test to ensure the image starts correctly
    CONTAINER_ID=$(docker run -d -p 8501:8501 \
        -e AWS_DEFAULT_REGION=us-east-1 \
        "${IMAGE_NAME}:${IMAGE_TAG}")
    
    log "Container started with ID: ${CONTAINER_ID}"
    
    # Wait a bit for the application to start
    sleep 10
    
    # Check if container is still running
    if docker ps | grep -q "${CONTAINER_ID}"; then
        log "✅ Container is running successfully"
        
        # Test health check
        if docker exec "${CONTAINER_ID}" python /tmp/health_check.py; then
            log "✅ Health check passed"
        else
            log "❌ Health check failed"
        fi
    else
        log "❌ Container failed to start or exited"
        docker logs "${CONTAINER_ID}"
    fi
    
    # Clean up test container
    docker stop "${CONTAINER_ID}" >/dev/null 2>&1 || true
    docker rm "${CONTAINER_ID}" >/dev/null 2>&1 || true
    
    log "Test completed and cleaned up"
}

# Main execution
main() {
    log "Starting Docker build process for PE-GPT..."
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        log "ERROR: Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Build the image
    build_image
    
    # Show image information
    show_image_info
    
    # Ask user if they want to test the image
    read -p "Do you want to test the image? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        test_image
    fi
    
    log "Docker build process completed successfully!"
    log "To run the container: docker run -p 8501:8501 -e AWS_DEFAULT_REGION=us-east-1 ${IMAGE_NAME}:${IMAGE_TAG}"
}

# Execute main function
main "$@"