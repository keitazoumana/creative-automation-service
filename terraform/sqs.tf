# Dead Letter Queue
resource "aws_sqs_queue" "campaign_dlq" {
  name                      = "${var.environment}-${var.project_name}-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-campaign-dlq"
      Description = "Dead letter queue for failed campaign processing"
    }
  )
}

# Main Campaign Processing Queue
resource "aws_sqs_queue" "campaign_queue" {
  name                       = "${var.environment}-${var.project_name}-queue"
  visibility_timeout_seconds = var.sqs_visibility_timeout
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Enable long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.campaign_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-campaign-queue"
      Description = "Main queue for campaign brief processing"
    }
  )
}

# SQS Queue Policy (allow S3 to send messages)
resource "aws_sqs_queue_policy" "allow_s3" {
  queue_url = aws_sqs_queue.campaign_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.campaign_queue.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_s3_bucket.campaign_bucket.arn
          }
        }
      }
    ]
  })
}
