#!/bin/bash

# PE-GPT Bedrock Demo Setup Script
# This script sets up demo AWS credentials for testing

echo "🔧 PE-GPT Bedrock Demo Setup"
echo "================================"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "⚠️  AWS CLI not found. Installing via pip..."
    pip3 install awscli
fi

echo ""
echo "📋 AWS Credentials Setup Options:"
echo ""
echo "1. Use AWS CLI to configure credentials:"
echo "   aws configure"
echo ""
echo "2. Set environment variables manually:"
echo "   export AWS_ACCESS_KEY_ID=your_access_key_id"
echo "   export AWS_SECRET_ACCESS_KEY=your_secret_access_key"
echo "   export AWS_REGION=us-east-1"
echo ""
echo "3. Use IAM role (for EC2/ECS environments)"
echo ""
echo "4. For demo/testing purposes, you can use mock credentials:"
echo "   (Note: This will not work with actual Bedrock API calls)"

read -p "Would you like to set up demo credentials for testing? (y/n): " setup_demo

if [[ $setup_demo =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔧 Setting up demo environment variables..."
    
    # Create a demo environment file
    cat > .env.demo << EOF
# Demo AWS Credentials (DO NOT USE IN PRODUCTION)
# These are placeholder values for testing the application structure
AWS_ACCESS_KEY_ID=demo_access_key_id
AWS_SECRET_ACCESS_KEY=demo_secret_access_key
AWS_REGION=us-east-1

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_MAX_TOKENS=5000
BEDROCK_TEMPERATURE=0.0
EOF

    echo "✅ Demo environment file created: .env.demo"
    echo ""
    echo "To use these demo credentials, run:"
    echo "   source .env.demo"
    echo "   streamlit run main.py"
    echo ""
    echo "⚠️  Note: Demo credentials will not work with actual AWS services."
    echo "   For real usage, please set up proper AWS credentials."
    
else
    echo ""
    echo "📖 Please refer to AWS_SETUP.md for detailed setup instructions."
fi

echo ""
echo "🚀 To start the application:"
echo "   streamlit run main.py"
echo ""
echo "📚 Documentation:"
echo "   - AWS_SETUP.md: AWS credentials setup"
echo "   - MIGRATION_GUIDE.md: Migration instructions"
echo "   - MIGRATION_SUMMARY.md: Complete migration summary"