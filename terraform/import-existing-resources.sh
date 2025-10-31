#!/bin/bash

# Import Existing Resources into Terraform State
# This script imports AWS resources that already exist to prevent creation errors

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Importing Existing AWS Resources${NC}"
echo -e "${GREEN}========================================${NC}"

# Source variables from tfvars
AWS_ACCOUNT_ID="385556511072"
ENVIRONMENT="dev"
PROJECT_NAME="creative-automation"
AWS_REGION="us-east-1"

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  Environment: $ENVIRONMENT"
echo "  Project: $PROJECT_NAME"
echo "  Region: $AWS_REGION"

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

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Import Summary${NC}"
echo -e "${GREEN}========================================${NC}"

# Show what's in state now
echo -e "\n${YELLOW}Resources now in Terraform state:${NC}"
terraform state list | grep -E "(ecr_repository|iam_role|iam_policy)" || echo "None found"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Import Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "  1. Run: terraform plan -var-file=\"environments/dev.tfvars\""
echo "  2. Verify no duplicate creation errors"
echo "  3. Run: ./deploy.sh -auto-approve"
