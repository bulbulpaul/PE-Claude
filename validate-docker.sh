#!/bin/bash

# PE-GPT Docker Validation Script
# This script validates the Docker setup and configuration

set -e

# Configuration
IMAGE_NAME="pe-gpt"
CONTAINER_NAME="pe-gpt-validation"
TEST_PORT="8502"  # Use different port to avoid conflicts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages with colors
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

log_info() {
    log "ℹ️  $1"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    log_success "Docker is available"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    log_success "Docker daemon is running"
    
    # Check required files
    local required_files=("Dockerfile" ".dockerignore" "docker-entrypoint.sh" "main.py" "requirements.txt")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done
    log_success "All required files are present"
}

# Function to validate Dockerfile
validate_dockerfile() {
    log_info "Validating Dockerfile..."
    
    # Check Dockerfile syntax
    if docker build -t "${IMAGE_NAME}:validation-test" -f Dockerfile . &> /dev/null; then
        log_success "Dockerfile builds successfully"
    else
        log_error "Dockerfile build failed"
        return 1
    fi
    
    # Check image size
    local image_size=$(docker images "${IMAGE_NAME}:validation-test" --format "{{.Size}}")
    log_info "Image size: $image_size"
    
    # Clean up test image
    docker rmi "${IMAGE_NAME}:validation-test" &> /dev/null || true
}

# Function to validate .dockerignore
validate_dockerignore() {
    log_info "Validating .dockerignore..."
    
    # Check if .dockerignore exists and has content
    if [ -s ".dockerignore" ]; then
        local ignored_count=$(wc -l < .dockerignore)
        log_success ".dockerignore contains $ignored_count ignore patterns"
    else
        log_warning ".dockerignore is empty or missing"
    fi
    
    # Check for common patterns
    local important_patterns=("__pycache__" "*.pyc" ".git" "venv" ".vscode")
    for pattern in "${important_patterns[@]}"; do
        if grep -q "$pattern" .dockerignore; then
            log_success "Found important ignore pattern: $pattern"
        else
            log_warning "Missing recommended ignore pattern: $pattern"
        fi
    done
}

# Function to validate startup script
validate_startup_script() {
    log_info "Validating startup script..."
    
    # Check if script is executable
    if [ -x "docker-entrypoint.sh" ]; then
        log_success "docker-entrypoint.sh is executable"
    else
        log_error "docker-entrypoint.sh is not executable"
        return 1
    fi
    
    # Check script syntax
    if bash -n docker-entrypoint.sh; then
        log_success "docker-entrypoint.sh syntax is valid"
    else
        log_error "docker-entrypoint.sh has syntax errors"
        return 1
    fi
}

# Function to test container functionality
test_container() {
    log_info "Testing container functionality..."
    
    # Build image
    log_info "Building test image..."
    if ! docker build -t "${IMAGE_NAME}:test" . &> /dev/null; then
        log_error "Failed to build Docker image"
        return 1
    fi
    log_success "Docker image built successfully"
    
    # Start container
    log_info "Starting test container..."
    local container_id
    container_id=$(docker run -d \
        --name "${CONTAINER_NAME}" \
        -p "${TEST_PORT}:8501" \
        -e AWS_DEFAULT_REGION=us-east-1 \
        "${IMAGE_NAME}:test")
    
    if [ $? -eq 0 ]; then
        log_success "Container started with ID: ${container_id:0:12}"
    else
        log_error "Failed to start container"
        return 1
    fi
    
    # Wait for application to start
    log_info "Waiting for application to start..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker exec "${CONTAINER_NAME}" curl -f http://localhost:8501/_stcore/health &> /dev/null; then
            log_success "Application is responding to health checks"
            break
        fi
        
        attempt=$((attempt + 1))
        sleep 2
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "Application failed to start within timeout"
            docker logs "${CONTAINER_NAME}"
            return 1
        fi
    done
    
    # Test external access
    log_info "Testing external access..."
    sleep 5  # Give a bit more time for full startup
    
    if curl -f "http://localhost:${TEST_PORT}/_stcore/health" &> /dev/null; then
        log_success "Application is accessible from host"
    else
        log_warning "Application may not be fully accessible from host (this might be normal for Streamlit)"
    fi
    
    # Check container health
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "unknown")
    log_info "Container health status: $health_status"
}

# Function to cleanup test resources
cleanup() {
    log_info "Cleaning up test resources..."
    
    # Stop and remove container
    docker stop "${CONTAINER_NAME}" &> /dev/null || true
    docker rm "${CONTAINER_NAME}" &> /dev/null || true
    
    # Remove test image
    docker rmi "${IMAGE_NAME}:test" &> /dev/null || true
    
    log_success "Cleanup completed"
}

# Function to show summary
show_summary() {
    log_info "Validation Summary:"
    echo "===================="
    echo "✅ Docker setup is ready for containerization"
    echo "✅ All required files are present and valid"
    echo "✅ Container builds and runs successfully"
    echo ""
    echo "Next steps:"
    echo "1. Build production image: ./docker-build.sh"
    echo "2. Run with Docker Compose: docker-compose up"
    echo "3. Deploy to ECS using the CDK stack"
    echo ""
    echo "For more information, see DOCKER_README.md"
}

# Main execution with error handling
main() {
    log_info "Starting PE-GPT Docker validation..."
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Run validation steps
    check_prerequisites
    validate_dockerfile
    validate_dockerignore
    validate_startup_script
    test_container
    
    # Show summary
    show_summary
    
    log_success "Docker validation completed successfully!"
}

# Execute main function
main "$@"