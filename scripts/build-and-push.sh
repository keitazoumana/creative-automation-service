#!/bin/bash
# Build and Push Lambda Docker Images to ECR
# Usage: ./build-and-push.sh [dev|staging|prod] [version]
# Example: ./build-and-push.sh dev v1.0.0

set -e

ENVIRONMENT=${1:-dev}
VERSION=${2:-latest}
echo "====================================="
echo " Creative Automation Service Builder"
echo "====================================="
echo ""
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"
echo ""

# Get AWS account ID
echo "Detecting AWS account..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --no-verify-ssl)

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to get AWS account ID. Check your AWS credentials."
    echo ""
    echo "Please disable ssl verifications"
    exit 1
fi

echo "AWS Account: $AWS_ACCOUNT_ID"

# Get AWS region
AWS_REGION=$(aws configure get region)
if [ -z "$AWS_REGION" ]; then
    AWS_REGION="us-east-1"
    echo "Using default region: $AWS_REGION"
else
    echo "AWS Region: $AWS_REGION"
fi

ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
PROJECT_NAME="creative-automation"

# Authenticate Docker to ECR
echo ""
echo "Authenticating Docker to ECR..."
aws ecr get-login-password --region $AWS_REGION --no-verify-ssl | docker login --username AWS --password-stdin $ECR_REGISTRY

if [ $? -ne 0 ]; then
    echo "ERROR: Docker authentication failed"
    exit 1
fi

echo "Docker authenticated successfully"

# Build and push each Lambda
LAMBDAS=("parser" "generator" "variants")
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BUILD_NUMBER="${VERSION}-${TIMESTAMP}"

echo "Build number: $BUILD_NUMBER"
echo ""

for LAMBDA in "${LAMBDAS[@]}"; do
    echo ""
    echo "========================================"
    echo " Building: $LAMBDA"
    echo "========================================"
    
    REPO_NAME="$PROJECT_NAME-$LAMBDA"
    IMAGE_URI="$ECR_REGISTRY/$REPO_NAME"
    
    # Create ECR repository if it doesn't exist
    echo "Checking ECR repository: $REPO_NAME"
    aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION --no-verify-ssl 2>/dev/null || \
    {
        echo "Creating ECR repository: $REPO_NAME"
        aws ecr create-repository \
            --repository-name $REPO_NAME \
            --region $AWS_REGION \
            --no-verify-ssl \
            --image-scanning-configuration scanOnPush=true \
            --tags Key=Environment,Value=$ENVIRONMENT Key=Project,Value=$PROJECT_NAME
    }
    
    # Build Docker image
    echo "Building Docker image..."
    docker build \
        --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
        --build-arg VERSION=$VERSION \
        -t $REPO_NAME \
        lambda/$LAMBDA
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Docker build failed for $LAMBDA"
        exit 1
    fi
    
    # Tag image with multiple tags
    echo "Tagging images:"
    echo "  - latest"
    echo "  - $VERSION"
    echo "  - $BUILD_NUMBER"
    
    docker tag "$REPO_NAME:latest" "$IMAGE_URI:latest"
    docker tag "$REPO_NAME:latest" "$IMAGE_URI:$VERSION"
    docker tag "$REPO_NAME:latest" "$IMAGE_URI:$BUILD_NUMBER"
    
    # Push all tags to ECR
    echo "Pushing to ECR..."
    docker push "$IMAGE_URI:latest"
    docker push "$IMAGE_URI:$VERSION"
    docker push "$IMAGE_URI:$BUILD_NUMBER"
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Docker push failed for $LAMBDA"
        exit 1
    fi
    
    echo "✓ Successfully pushed $LAMBDA to ECR"
    echo "  Image URI: $IMAGE_URI:$VERSION"
done

echo ""
echo "========================================"
echo " Build Complete!"
echo "========================================"
echo ""
echo "All Lambda images built and pushed to ECR."
echo ""
echo "Build Information:"
echo "  Environment: $ENVIRONMENT"
echo "  Version: $VERSION"
echo "  Build Number: $BUILD_NUMBER"
echo "  ECR Registry: $ECR_REGISTRY"
echo ""
echo "Images pushed:"
for LAMBDA in "${LAMBDAS[@]}"; do
    echo "  - $ECR_REGISTRY/$PROJECT_NAME-$LAMBDA:$VERSION"
done
echo ""
echo "Next steps:"
echo "  1. Update terraform/environments/$ENVIRONMENT.tfvars with:"
echo "     ecr_image_tag = \"$VERSION\""
echo ""
echo "  2. Deploy infrastructure:"
echo "     cd terraform"
echo "     terraform apply -var-file=environments/$ENVIRONMENT.tfvars"
echo ""
echo "To use a specific version for Lambda functions, run:"
echo "  export TF_VAR_ecr_image_tag=\"$VERSION\""
echo "  terraform apply -var-file=environments/$ENVIRONMENT.tfvars"
echo ""
