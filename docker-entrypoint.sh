#!/bin/sh

# PE-GPT Docker Entrypoint Script
set -e

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Check required environment variables
if [ -z "$AWS_DEFAULT_REGION" ]; then
    log "WARNING: AWS_DEFAULT_REGION not set, using default: us-east-1"
    export AWS_DEFAULT_REGION="us-east-1"
fi

if [ -z "$BEDROCK_KB_ID" ]; then
    log "WARNING: BEDROCK_KB_ID not set. Application may not function properly."
fi

# Set Streamlit configuration
export STREAMLIT_SERVER_HEADLESS=${STREAMLIT_SERVER_HEADLESS:-true}
export STREAMLIT_SERVER_PORT=${STREAMLIT_SERVER_PORT:-8501}
export STREAMLIT_SERVER_ADDRESS=${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}

log "Starting PE-GPT application..."
log "AWS Region: $AWS_DEFAULT_REGION"
log "Bedrock KB ID: ${BEDROCK_KB_ID:-'Not set'}"
log "Streamlit Port: $STREAMLIT_SERVER_PORT"

# Start the Streamlit application
exec streamlit run main.py \
    --server.port=$STREAMLIT_SERVER_PORT \
    --server.address=$STREAMLIT_SERVER_ADDRESS \
    --server.headless=$STREAMLIT_SERVER_HEADLESS \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false