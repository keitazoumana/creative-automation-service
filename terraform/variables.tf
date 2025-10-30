variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS Account ID (get with: aws sts get-caller-identity --query Account --output text)"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name for campaign storage (must be globally unique)"
  type        = string
}

variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "creative-automation"
}

# SQS Configuration
variable "sqs_visibility_timeout" {
  description = "SQS visibility timeout in seconds"
  type        = number
  default     = 300
}

variable "sqs_max_receive_count" {
  description = "Maximum times a message can be received before moving to DLQ"
  type        = number
  default     = 3
}

# Lambda Configuration - Parser
variable "lambda_parser_memory" {
  description = "Memory allocation for parser Lambda (MB)"
  type        = number
  default     = 512
}

variable "lambda_parser_timeout" {
  description = "Timeout for parser Lambda (seconds)"
  type        = number
  default     = 300
}

# Lambda Configuration - Generator
variable "lambda_generator_memory" {
  description = "Memory allocation for image generator Lambda (MB)"
  type        = number
  default     = 1024
}

variable "lambda_generator_timeout" {
  description = "Timeout for image generator Lambda (seconds)"
  type        = number
  default     = 120
}

# Lambda Configuration - Variants
variable "lambda_variants_memory" {
  description = "Memory allocation for variants generator Lambda (MB)"
  type        = number
  default     = 2048
}

variable "lambda_variants_timeout" {
  description = "Timeout for variants generator Lambda (seconds)"
  type        = number
  default     = 180
}

# ECR Configuration
variable "ecr_image_tag" {
  description = "ECR image tag to deploy"
  type        = string
  default     = "latest"
}

# Amazon Bedrock Configuration
variable "bedrock_model_id" {
  description = "Bedrock model ID for image generation"
  type        = string
  default     = "amazon.titan-image-generator-v1"
}

# CloudWatch Configuration
variable "cloudwatch_log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

# Tags
variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
