#!/bin/bash

# Import Existing Resources into Terraform State
# This script imports AWS resources that already exist to prevent creation errors

set +e  # Don't exit on error - we want to try importing all resources

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Importing Existing AWS Resources${NC}"
echo -e "${GREEN}========================================${NC}"

# Prompt for environment
echo -e "\n${BLUE}Select environment (dev/staging/production):${NC}"
read -p "Environment [dev]: " ENVIRONMENT
ENVIRONMENT=${ENVIRONMENT:-dev}

# Read configuration from tfvars file
TFVARS_FILE="environments/${ENVIRONMENT}.tfvars"

if [ ! -f "$TFVARS_FILE" ]; then
    echo -e "${RED}Error: $TFVARS_FILE not found!${NC}"
    exit 1
fi

# Extract values from tfvars
AWS_ACCOUNT_ID=$(grep -E '^aws_account_id' "$TFVARS_FILE" | sed 's/.*= *"\(.*\)".*/\1/')
AWS_REGION=$(grep -E '^aws_region' "$TFVARS_FILE" | sed 's/.*= *"\(.*\)".*/\1/')
PROJECT_NAME=$(grep -E '^project_name' "$TFVARS_FILE" | sed 's/.*= *"\(.*\)".*/\1/')
S3_BUCKET_NAME=$(grep -E '^s3_bucket_name' "$TFVARS_FILE" | sed 's/.*= *"\(.*\)".*/\1/')

echo -e "\n${YELLOW}Configuration loaded from $TFVARS_FILE:${NC}"
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  Environment: $ENVIRONMENT"
echo "  Project: $PROJECT_NAME"
echo "  Region: $AWS_REGION"
echo "  S3 Bucket: $S3_BUCKET_NAME"

# Function to import resource with error handling
import_resource() {
    local resource_type=$1
    local resource_name=$2
    local resource_id=$3
    
    echo -e "\n${YELLOW}Checking: ${resource_type}.${resource_name}${NC}"
    
    # Check if resource already exists in state
    if terraform state show "${resource_type}.${resource_name}" &>/dev/null; then
        echo -e "${GREEN}✓ Already in state, skipping${NC}"
        return 0
    fi
    
    # Try to import
    echo -e "${YELLOW}Importing: ${resource_id}${NC}"
    if terraform import "${resource_type}.${resource_name}" "${resource_id}" 2>/dev/null; then
        echo -e "${GREEN}✓ Successfully imported${NC}"
    else
        echo -e "${RED}✗ Import failed (resource may not exist in AWS)${NC}"
    fi
}

echo -e "\n${GREEN}========================================${NC}"
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  Environment: $ENVIRONMENT"
echo "  Project: $PROJECT_NAME"
echo "  Region: $AWS_REGION"
echo "  S3 Bucket: $S3_BUCKET_NAME"

echo -e "\n${BLUE}This will import ALL existing AWS resources into Terraform state.${NC}"
echo -e "${BLUE}Resources already in state will be skipped.${NC}"
read -p "Continue? (y/n) [y]: " CONFIRM
CONFIRM=${CONFIRM:-y}

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo -e "${YELLOW}Import cancelled.${NC}"
    exit 0
fi

# Function to import resource with error handling
import_resource() {
    local resource_type=$1
    local resource_name=$2
    local resource_id=$3
    
    echo -e "\n${YELLOW}Checking: ${resource_type}.${resource_name}${NC}"
    
    # Check if resource already exists in state
    if terraform state show "${resource_type}.${resource_name}" &>/dev/null; then
        echo -e "${GREEN}✓ Already in state, skipping${NC}"
        return 0
    fi
    
    # Try to import
    echo -e "${YELLOW}Importing: ${resource_id}${NC}"
    if terraform import "${resource_type}.${resource_name}" "${resource_id}" 2>&1 | grep -q "successfully"; then
        echo -e "${GREEN}✓ Successfully imported${NC}"
        return 0
    else
        echo -e "${RED}✗ Import failed (resource may not exist in AWS)${NC}"
        return 1
    fi
}

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Step 1: Import ECR Repositories${NC}"
echo -e "${GREEN}========================================${NC}"

import_resource "aws_ecr_repository" "parser" "${PROJECT_NAME}-parser"
import_resource "aws_ecr_repository" "generator" "${PROJECT_NAME}-generator"
import_resource "aws_ecr_repository" "variants" "${PROJECT_NAME}-variants"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Step 2: Import IAM Resources${NC}"
echo -e "${GREEN}========================================${NC}"

import_resource "aws_iam_role" "lambda_role" "${ENVIRONMENT}-${PROJECT_NAME}-lambda-role"
import_resource "aws_iam_policy" "lambda_policy" "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${ENVIRONMENT}-${PROJECT_NAME}-lambda-policy"
import_resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" "${ENVIRONMENT}-${PROJECT_NAME}-lambda-role/arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${ENVIRONMENT}-${PROJECT_NAME}-lambda-policy"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Step 3: Import S3 Bucket and Configuration${NC}"
echo -e "${GREEN}========================================${NC}"

import_resource "aws_s3_bucket" "campaign_bucket" "${S3_BUCKET_NAME}"
import_resource "aws_s3_bucket_versioning" "campaign_bucket" "${S3_BUCKET_NAME}"
import_resource "aws_s3_bucket_server_side_encryption_configuration" "campaign_bucket" "${S3_BUCKET_NAME}"
import_resource "aws_s3_bucket_public_access_block" "campaign_bucket" "${S3_BUCKET_NAME}"
import_resource "aws_s3_bucket_lifecycle_configuration" "campaign_bucket" "${S3_BUCKET_NAME}"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Step 4: Import SQS Queues${NC}"
echo -e "${GREEN}========================================${NC}"

# Get SQS queue URLs
DLQ_URL="https://sqs.${AWS_REGION}.amazonaws.com/${AWS_ACCOUNT_ID}/${ENVIRONMENT}-${PROJECT_NAME}-dlq"
QUEUE_URL="https://sqs.${AWS_REGION}.amazonaws.com/${AWS_ACCOUNT_ID}/${ENVIRONMENT}-${PROJECT_NAME}-queue"

import_resource "aws_sqs_queue" "campaign_dlq" "$DLQ_URL"
import_resource "aws_sqs_queue" "campaign_queue" "$QUEUE_URL"
import_resource "aws_sqs_queue_policy" "allow_s3" "$QUEUE_URL"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Step 5: Import Lambda Functions${NC}"
echo -e "${GREEN}========================================${NC}"

import_resource "aws_lambda_function" "parser" "${ENVIRONMENT}-${PROJECT_NAME}-parser"
import_resource "aws_lambda_function" "generator" "${ENVIRONMENT}-${PROJECT_NAME}-generator"
import_resource "aws_lambda_function" "variants" "${ENVIRONMENT}-${PROJECT_NAME}-variants"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Step 6: Import Lambda Event Source Mappings${NC}"
echo -e "${GREEN}========================================${NC}"

# Note: Event source mappings need to be imported by UUID
# We'll try to find them, but they might not exist yet
echo -e "${YELLOW}Note: Lambda event source mappings will be created during deployment if they don't exist${NC}"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Step 7: Import CloudWatch Log Groups${NC}"
echo -e "${GREEN}========================================${NC}"

import_resource "aws_cloudwatch_log_group" "parser" "/aws/lambda/${ENVIRONMENT}-${PROJECT_NAME}-parser"
import_resource "aws_cloudwatch_log_group" "generator" "/aws/lambda/${ENVIRONMENT}-${PROJECT_NAME}-generator"
import_resource "aws_cloudwatch_log_group" "variants" "/aws/lambda/${ENVIRONMENT}-${PROJECT_NAME}-variants"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Step 8: Import S3 Notification${NC}"
echo -e "${GREEN}========================================${NC}"

# S3 notifications are trickier - they use the bucket name as the ID
import_resource "aws_s3_bucket_notification" "campaign_upload" "${S3_BUCKET_NAME}"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Import Summary${NC}"
echo -e "${GREEN}========================================${NC}"

# Show what's in state now
echo -e "\n${YELLOW}All resources now in Terraform state:${NC}"
terraform state list

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Import Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "  1. Run: terraform plan -var-file=\"environments/${ENVIRONMENT}.tfvars\""
echo "  2. Verify no duplicate creation errors"
echo "  3. Run: ./deploy.sh -auto-approve"

