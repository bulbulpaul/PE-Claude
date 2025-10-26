#!/bin/bash

# PE-GPT Docker Container Startup Script
# This script handles container initialization and health checks

set -e

# Function to log messages with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if required environment variables are set
check_environment() {
    log "Checking environment variables..."
    
    # Check AWS region
    if [ -z "$AWS_DEFAULT_REGION" ]; then
        log "WARNING: AWS_DEFAULT_REGION not set, using default: us-east-1"
        export AWS_DEFAULT_REGION="us-east-1"
    fi
    
    # Check Bedrock KB ID (optional)
    if [ -z "$BEDROCK_KB_ID" ]; then
        log "INFO: BEDROCK_KB_ID not set, running in local mode"
    else
        log "INFO: BEDROCK_KB_ID configured, Bedrock integration enabled"
    fi
    
    log "Environment check completed"
}

# Function to validate application files
validate_app() {
    log "Validating application files..."
    
    if [ ! -f "main.py" ]; then
        log "ERROR: main.py not found"
        exit 1
    fi
    
    if [ ! -d "core" ]; then
        log "ERROR: core directory not found"
        exit 1
    fi
    
    log "Application validation completed"
}

# Function to create health check endpoint
setup_health_check() {
    log "Setting up health check..."
    
    # Create a simple health check script
    cat > /tmp/health_check.py << 'EOF'
import requests
import sys
import time

def health_check():
    try:
        # Wait a bit for Streamlit to fully start
        time.sleep(2)
        
        # Check Streamlit health endpoint
        response = requests.get('http://localhost:8501/_stcore/health', timeout=5)
        
        if response.status_code == 200:
            print("Health check passed")
            return True
        else:
            print(f"Health check failed with status: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Health check failed with error: {e}")
        return False

if __name__ == "__main__":
    if health_check():
        sys.exit(0)
    else:
        sys.exit(1)
EOF
    
    log "Health check setup completed"
}

# Function to start the application
start_application() {
    log "Starting PE-GPT application..."
    
    # Set Streamlit configuration
    export STREAMLIT_SERVER_HEADLESS=true
    export STREAMLIT_SERVER_PORT=8501
    export STREAMLIT_SERVER_ADDRESS=0.0.0.0
    export STREAMLIT_SERVER_ENABLE_CORS=false
    export STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
    
    # Start Streamlit application
    log "Launching Streamlit on port 8501..."
    exec streamlit run main.py \
        --server.port=8501 \
        --server.address=0.0.0.0 \
        --server.headless=true \
        --server.enableCORS=false \
        --server.enableXsrfProtection=false \
        --browser.gatherUsageStats=false
}

# Function to handle shutdown gracefully
cleanup() {
    log "Received shutdown signal, cleaning up..."
    # Kill any background processes if needed
    pkill -f streamlit || true
    log "Cleanup completed"
    exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGTERM SIGINT

# Main execution
main() {
    log "Starting PE-GPT container initialization..."
    
    # Run initialization steps
    check_environment
    validate_app
    setup_health_check
    
    log "Initialization completed, starting application..."
    
    # Start the application (this will exec and replace the shell)
    start_application
}

# Execute main function
main "$@"