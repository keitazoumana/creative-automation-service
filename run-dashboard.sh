#!/bin/bash
# Launch Streamlit Dashboard for Creative Automation Service

echo "========================================"
echo "  Creative Automation Service Dashboard"
echo "========================================"
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found. Installing dependencies..."
    pip install -r requirements-app.txt
fi

# Check AWS credentials
if ! aws sts get-caller-identity --no-verify-ssl &> /dev/null; then
    echo "❌ AWS credentials not configured"
    echo "Run: aws configure"
    exit 1
fi

echo "✅ AWS credentials verified"
echo ""

# Get bucket name from terraform output
if [ -f "terraform/terraform.tfstate" ]; then
    export S3_BUCKET_NAME=$(cd terraform && terraform output -raw campaign_bucket_name 2>/dev/null)
    echo "✅ S3 Bucket: $S3_BUCKET_NAME"
fi

# Set defaults if not found
export S3_BUCKET_NAME=${S3_BUCKET_NAME:-"creative-automation-dev-keita-2025"}
export ENVIRONMENT=${ENVIRONMENT:-"dev"}
export PROJECT_NAME=${PROJECT_NAME:-"creative-automation"}

echo "🚀 Launching Streamlit Dashboard..."
echo "📍 URL: http://localhost:8501"
echo ""

# Launch Streamlit
streamlit run app.py
