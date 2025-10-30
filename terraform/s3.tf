# S3 Bucket for Campaign Storage
resource "aws_s3_bucket" "campaign_bucket" {
  bucket = var.s3_bucket_name
}

# Enable versioning
resource "aws_s3_bucket_versioning" "campaign_bucket" {
  bucket = aws_s3_bucket.campaign_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "campaign_bucket" {
  bucket = aws_s3_bucket.campaign_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "campaign_bucket" {
  bucket = aws_s3_bucket.campaign_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Event Notification → SQS
resource "aws_s3_bucket_notification" "campaign_upload" {
  bucket = aws_s3_bucket.campaign_bucket.id

  queue {
    queue_arn     = aws_sqs_queue.campaign_queue.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "input/campaign-briefs/"
    filter_suffix = ".json"
  }

  depends_on = [aws_sqs_queue_policy.allow_s3]
}

# Lifecycle policy (cleanup old campaigns after 90 days)
resource "aws_s3_bucket_lifecycle_configuration" "campaign_bucket" {
  bucket = aws_s3_bucket.campaign_bucket.id

  rule {
    id     = "cleanup-old-campaigns"
    status = "Enabled"

    filter {
      prefix = "output/"
    }

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
