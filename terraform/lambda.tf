# Lambda Function: Campaign Brief Parser
resource "aws_lambda_function" "parser" {
  function_name = "${var.environment}-${var.project_name}-parser"
  role          = aws_iam_role.lambda_role.arn
  
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.parser.repository_url}:${var.ecr_image_tag}"
  
  memory_size                    = var.lambda_parser_memory
  timeout                        = var.lambda_parser_timeout
  
  environment {
    variables = {
      ENVIRONMENT           = var.environment
      S3_BUCKET_NAME       = aws_s3_bucket.campaign_bucket.id
      GENERATOR_FUNCTION   = "${var.environment}-${var.project_name}-generator"
      VARIANTS_FUNCTION    = "${var.environment}-${var.project_name}-variants"
      LOG_LEVEL            = "INFO"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy_attachment
  ]

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-parser"
      Description = "Parse campaign briefs and orchestrate processing"
    }
  )
}

# Lambda Function: AI Image Generator
resource "aws_lambda_function" "generator" {
  function_name = "${var.environment}-${var.project_name}-generator"
  role          = aws_iam_role.lambda_role.arn
  
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.generator.repository_url}:${var.ecr_image_tag}"
  
  memory_size                    = var.lambda_generator_memory
  timeout                        = var.lambda_generator_timeout
  
  environment {
    variables = {
      ENVIRONMENT        = var.environment
      S3_BUCKET_NAME     = aws_s3_bucket.campaign_bucket.id
      VARIANTS_FUNCTION  = "${var.environment}-${var.project_name}-variants"
      BEDROCK_MODEL_ID   = var.bedrock_model_id
      LOG_LEVEL          = "INFO"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy_attachment
  ]

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-generator"
      Description = "Generate images using Amazon Bedrock"
    }
  )
}

# Lambda Function: Variants Generator
resource "aws_lambda_function" "variants" {
  function_name = "${var.environment}-${var.project_name}-variants"
  role          = aws_iam_role.lambda_role.arn
  
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.variants.repository_url}:${var.ecr_image_tag}"
  
  memory_size                    = var.lambda_variants_memory
  timeout                        = var.lambda_variants_timeout
  
  environment {
    variables = {
      ENVIRONMENT    = var.environment
      S3_BUCKET_NAME = aws_s3_bucket.campaign_bucket.id
      LOG_LEVEL      = "INFO"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy_attachment
  ]

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-variants"
      Description = "Create multiple aspect ratio variants"
    }
  )
}

# SQS Event Source Mapping (triggers parser Lambda)
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.campaign_queue.arn
  function_name    = aws_lambda_function.parser.arn
  
  batch_size                         = 1
  maximum_batching_window_in_seconds = 0
  
  function_response_types = ["ReportBatchItemFailures"]
  
  depends_on = [
    aws_lambda_function.parser,
    aws_sqs_queue.campaign_queue
  ]
}
