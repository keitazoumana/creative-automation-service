# S3 Bucket
output "s3_bucket_name" {
  description = "Name of the S3 bucket for campaign storage"
  value       = aws_s3_bucket.campaign_bucket.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.campaign_bucket.arn
}

# SQS
output "sqs_queue_url" {
  description = "URL of the campaign processing SQS queue"
  value       = aws_sqs_queue.campaign_queue.url
}

output "sqs_dlq_url" {
  description = "URL of the Dead Letter Queue"
  value       = aws_sqs_queue.campaign_dlq.url
}

# ECR
output "ecr_parser_repository_url" {
  description = "ECR repository URL for parser Lambda"
  value       = aws_ecr_repository.parser.repository_url
}

output "ecr_generator_repository_url" {
  description = "ECR repository URL for generator Lambda"
  value       = aws_ecr_repository.generator.repository_url
}

output "ecr_variants_repository_url" {
  description = "ECR repository URL for variants Lambda"
  value       = aws_ecr_repository.variants.repository_url
}

# Lambda Functions
output "lambda_parser_name" {
  description = "Name of the parser Lambda function"
  value       = aws_lambda_function.parser.function_name
}

output "lambda_parser_arn" {
  description = "ARN of the parser Lambda function"
  value       = aws_lambda_function.parser.arn
}

output "lambda_generator_name" {
  description = "Name of the generator Lambda function"
  value       = aws_lambda_function.generator.function_name
}

output "lambda_generator_arn" {
  description = "ARN of the generator Lambda function"
  value       = aws_lambda_function.generator.arn
}

output "lambda_variants_name" {
  description = "Name of the variants Lambda function"
  value       = aws_lambda_function.variants.function_name
}

output "lambda_variants_arn" {
  description = "ARN of the variants Lambda function"
  value       = aws_lambda_function.variants.arn
}

# CloudWatch Log Groups (commented out)
# output "cloudwatch_parser_log_group" {
#   description = "CloudWatch log group for parser Lambda"
#   value       = aws_cloudwatch_log_group.parser.name
# }

# output "cloudwatch_generator_log_group" {
#   description = "CloudWatch log group for generator Lambda"
#   value       = aws_cloudwatch_log_group.generator.name
# }

# output "cloudwatch_variants_log_group" {
#   description = "CloudWatch log group for variants Lambda"
#   value       = aws_cloudwatch_log_group.variants.name
# }

# Quick Start Commands
output "quick_start_commands" {
  description = "Commands to get started"
  value = <<-EOT
  
  ========================================
  🎉 Deployment Complete!
  ========================================
  
  📦 S3 Bucket: ${aws_s3_bucket.campaign_bucket.id}
  📬 SQS Queue: ${aws_sqs_queue.campaign_queue.name}
  
  Next Steps:
  
  1. Build and push Docker images:
     cd ..
     ./scripts/build-and-push.sh ${data.aws_caller_identity.current.account_id}
  
  2. Upload a test campaign:
     aws s3 cp examples/campaign-briefs/01-simple-nike.json s3://${aws_s3_bucket.campaign_bucket.id}/input/campaign-briefs/
  
  3. Monitor processing:
     aws logs tail /aws/lambda/${aws_lambda_function.parser.function_name} --follow
  
  4. Check results:
     aws s3 ls s3://${aws_s3_bucket.campaign_bucket.id}/output/ --recursive
  
  ========================================
  EOT
}
