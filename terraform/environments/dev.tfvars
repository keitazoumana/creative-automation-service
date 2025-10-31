# AWS Account: YOUR_AWS_ACCOUNT_ID
# Environment: Development (POC)
# Region: us-east-1 (required for Bedrock)

aws_account_id = "YOUR_AWS_ACCOUNT_ID"
aws_region     = "us-east-1"

# S3 Configuration
# IMPORTANT: Bucket names must be globally unique across ALL AWS accounts
# Change "yourname" to something unique if this name is taken
s3_bucket_name = "creative-automation-dev-yourname-2025"

# Project Configuration
environment  = "dev"
project_name = "creative-automation"

# Lambda Configuration - Parser
lambda_parser_memory  = 512
lambda_parser_timeout = 300

# Lambda Configuration - Generator
lambda_generator_memory  = 1024
lambda_generator_timeout = 120

# Lambda Configuration - Variants
lambda_variants_memory  = 2048
lambda_variants_timeout = 180

# SQS Configuration
sqs_visibility_timeout = 300
sqs_max_receive_count  = 3

# ECR Configuration
ecr_image_tag = "1.1.3"

# Amazon Bedrock Configuration
bedrock_model_id = "amazon.titan-image-generator-v1"

# CloudWatch Configuration
cloudwatch_log_retention_days = 7

# Resource Tags
tags = {
  Project     = "CreativeAutomation"
  Environment = "dev"
  ManagedBy   = "Terraform"
  Owner       = "YourName"
  Purpose     = "POC"
}