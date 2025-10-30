# Deployment Guide

Complete step-by-step guide to deploy the Creative Automation Service to your AWS account.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [Clone and Configure](#clone-and-configure)
4. [Build Lambda Images](#build-lambda-images)
5. [Deploy Infrastructure](#deploy-infrastructure)
6. [Test the Pipeline](#test-the-pipeline)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

### Required Tools
- **AWS Account** with admin access
- **AWS CLI v2** ([Install](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))
- **Terraform ≥ 1.5** ([Install](https://developer.hashicorp.com/terraform/install))
- **Docker Desktop** ([Install](https://www.docker.com/products/docker-desktop/))
- **Git** ([Install](https://git-scm.com/downloads))

### AWS Prerequisites
- **Bedrock Access**: Stable Diffusion XL model enabled in us-east-1
- **IAM Permissions**: Ability to create S3, Lambda, ECR, IAM, SQS, CloudWatch
- **Budget**: ~$44/month for 100 campaigns ($0.44 per campaign)

### Check Your Setup
```bash
# Verify installations
aws --version          # Should show v2.x
terraform --version    # Should show v1.5+
docker --version       # Should show 20.x+
git --version          # Should show 2.x+

# Verify AWS credentials
aws sts get-caller-identity
```

---

## AWS Account Setup

### 1. Configure AWS CLI

If not already configured:
```bash
aws configure
```

Enter:
- **AWS Access Key ID**: Your IAM user access key
- **AWS Secret Access Key**: Your secret key
- **Default region**: `us-east-1` (required for Bedrock)
- **Output format**: `json`

### 2. Enable Amazon Bedrock

**CRITICAL**: You must enable Stable Diffusion XL model access.

1. Open [AWS Console → Bedrock](https://console.aws.amazon.com/bedrock/)
2. Navigate to **Model access** (left sidebar)
3. Click **Modify model access**
4. Find **Stability AI → Stable Diffusion XL**
5. Check the box and click **Save changes**
6. Wait 2-3 minutes for access to be granted
7. Verify status shows **Access granted**

> ⚠️ **Without this step, image generation will fail with access denied errors.**

### 3. Verify Your Account ID

```bash
# Get your AWS account ID
aws sts get-caller-identity --query Account --output text

# Save this - you'll need it for configuration
```

---

## Clone and Configure

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/creative-automation-service.git
cd creative-automation-service
```

### 2. Create Environment Configuration

Copy the example config and customize:

```bash
# Copy the dev environment template
cp terraform/environments/dev.tfvars.example terraform/environments/dev.tfvars
```

### 3. Edit `terraform/environments/dev.tfvars`

Open the file in your editor and replace placeholders:

```hcl
# REPLACE THIS with your AWS account ID
aws_account_id = "123456789012"  # Run: aws sts get-caller-identity --query Account --output text

# REPLACE THIS with a globally unique bucket name
s3_bucket_name = "creative-automation-dev-YOUR-NAME-12345"  # Must be unique across all AWS

# REPLACE THIS with your AWS region (must be us-east-1 for Bedrock)
aws_region = "us-east-1"

# Customize these if needed
environment = "dev"
project_name = "creative-automation"

# Lambda configuration (adjust based on your needs)
parser_lambda_memory = 512
parser_lambda_timeout = 300

generator_lambda_memory = 1024
generator_lambda_timeout = 120

variants_lambda_memory = 2048
variants_lambda_timeout = 180

# ECR image tag
ecr_image_tag = "latest"  # Use "latest" for dev, version tags for prod

# CloudWatch logs
cloudwatch_log_retention_days = 7

# Tags
tags = {
  Project     = "CreativeAutomation"
  Environment = "dev"
  ManagedBy   = "Terraform"
  Owner       = "YourName"  # REPLACE with your name
}
```

> 💡 **Tip**: Use your name/initials in the bucket name to ensure uniqueness.  
> Example: `creative-automation-dev-jsmith-98765`

---

## Build Lambda Images

The Lambda functions run as Docker containers in ECR.

### 1. Make Build Script Executable (Linux/Mac)

```bash
chmod +x scripts/build-and-push.sh
```

### 2. Build and Push Images

**Windows (PowerShell)**:
```powershell
.\scripts\build-and-push.ps1 dev
```

**Linux/Mac (Bash)**:
```bash
./scripts/build-and-push.sh dev
```

This script will:
1. Detect your AWS account ID
2. Authenticate Docker to ECR
3. Create ECR repositories (if needed)
4. Build 3 Lambda Docker images (parser, generator, variants)
5. Tag images with `latest` and timestamp
6. Push to ECR

**Expected output**:
```
=====================================
 Creative Automation Service Builder
=====================================

Detecting AWS account...
AWS Account: 123456789012
AWS Region: us-east-1

Authenticating Docker to ECR...
Docker authenticated successfully

========================================
 Building: parser
========================================
...
✓ Successfully pushed parser to ECR

========================================
 Building: generator
========================================
...
✓ Successfully pushed generator to ECR

========================================
 Building: variants
========================================
...
✓ Successfully pushed variants to ECR

========================================
 Build Complete!
========================================
```

> ⏱️ **Time**: 5-10 minutes depending on your internet speed

---

## Deploy Infrastructure

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

This downloads AWS provider and initializes backend.

### 2. Plan Deployment

Preview what will be created:

```bash
terraform plan -var-file=environments/dev.tfvars
```

Review the output. You should see:
- 1 S3 bucket
- 2 SQS queues (main + DLQ)
- 3 ECR repositories
- 3 Lambda functions
- 1 IAM role + policy
- 3 CloudWatch log groups
- 1 CloudWatch alarm

**Expected resource count**: ~20 resources

### 3. Deploy

```bash
terraform apply -var-file=environments/dev.tfvars
```

Type `yes` when prompted.

**Expected output**:
```
Apply complete! Resources: 20 added, 0 changed, 0 destroyed.

Outputs:

campaign_bucket_name = "creative-automation-dev-jsmith-98765"
cloudwatch_log_groups = {
  "generator" = "/aws/lambda/dev-creative-automation-generator"
  "parser" = "/aws/lambda/dev-creative-automation-parser"
  "variants" = "/aws/lambda/dev-creative-automation-variants"
}
...
quick_start_commands = <<EOT
✅ Deployment complete!

S3 Bucket: creative-automation-dev-jsmith-98765

Next steps:
1. Upload a campaign brief:
   aws s3 cp examples/campaign-briefs/01-simple-nike.json s3://creative-automation-dev-jsmith-98765/input/campaign-briefs/

2. Monitor processing:
   aws logs tail /aws/lambda/dev-creative-automation-parser --follow

3. Check results:
   aws s3 ls s3://creative-automation-dev-jsmith-98765/output/ --recursive
EOT
```

> ⏱️ **Time**: 2-3 minutes

---

## Test the Pipeline

### 1. Upload Test Campaign

Use the simple Nike example:

```bash
# From project root
aws s3 cp examples/campaign-briefs/01-simple-nike.json \
  s3://YOUR-BUCKET-NAME/input/campaign-briefs/
```

Replace `YOUR-BUCKET-NAME` with your actual bucket from Terraform outputs.

### 2. Monitor Processing

**Watch parser logs**:
```bash
aws logs tail /aws/lambda/dev-creative-automation-parser --follow
```

You should see:
```
Processing: s3://creative-automation-dev-jsmith-98765/input/campaign-briefs/01-simple-nike.json
Saved manifest: s3://...
Generating new image for: Nike Air Max 270
```

**Watch generator logs** (in another terminal):
```bash
aws logs tail /aws/lambda/dev-creative-automation-generator --follow
```

**Watch variants logs**:
```bash
aws logs tail /aws/lambda/dev-creative-automation-variants --follow
```

### 3. Check Results

After ~2-3 minutes, check the output:

```bash
# List output files
aws s3 ls s3://YOUR-BUCKET-NAME/output/ --recursive

# Download manifest
aws s3 cp s3://YOUR-BUCKET-NAME/output/nike-air-max-spring-launch-TIMESTAMP/manifest.json -
```

**Expected manifest**:
```json
{
  "campaign_id": "nike-air-max-spring-launch-20250123-143022",
  "campaign_name": "Nike Air Max Spring Launch",
  "status": "completed",
  "total_cost": 0.44,
  "products": [
    {
      "product_name": "Nike Air Max 270",
      "image_source": "generated",
      "generation_cost": 0.30,
      "processing_cost": 0.01,
      "variants_count": 5,
      "variants": [
        {"platform": "instagram-square", "key": "output/.../variants/..."},
        {"platform": "instagram-story", "key": "output/.../variants/..."},
        ...
      ]
    }
  ]
}
```

### 4. Download Variants

```bash
# Download all variants
aws s3 sync s3://YOUR-BUCKET-NAME/output/CAMPAIGN-ID/variants/ ./test-output/
```

Open the images in your browser to verify quality.

---

## Monitoring

### CloudWatch Dashboards

```bash
# View Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=dev-creative-automation-parser \
  --start-time 2025-01-23T00:00:00Z \
  --end-time 2025-01-23T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

### Check SQS Queue

```bash
# Check main queue
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw sqs_queue_url) \
  --attribute-names ApproximateNumberOfMessages

# Check dead letter queue
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw sqs_dlq_url) \
  --attribute-names ApproximateNumberOfMessages
```

### Cost Monitoring

```bash
# Get cost estimate (requires Cost Explorer)
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://cost-filter.json
```

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

### Common Issues

**"Bedrock access denied"**:
- Enable Stable Diffusion XL model access in Bedrock console
- Wait 2-3 minutes after enabling

**"Bucket already exists"**:
- S3 bucket names must be globally unique
- Use your name/initials in the bucket name

**"Docker authentication failed"**:
```bash
# Re-authenticate
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin YOUR-ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
```

**"Lambda timeout"**:
- Check CloudWatch logs for errors
- Increase `timeout` in dev.tfvars
- Verify Bedrock is responding

**Messages in DLQ**:
```bash
# Check DLQ messages
aws sqs receive-message --queue-url $(terraform output -raw sqs_dlq_url)
```

---

## Clean Up

To avoid ongoing charges, destroy all resources:

```bash
# From terraform/ directory
terraform destroy -var-file=environments/dev.tfvars
```

Type `yes` to confirm.

> ⚠️ **This will delete**:
> - All S3 bucket contents (campaigns, outputs)
> - All Lambda functions
> - ECR repositories and images
> - SQS queues and messages
> - CloudWatch logs

---

## Next Steps

- **Production Deployment**: Use `terraform/environments/prod.tfvars.example`
- **CI/CD**: Set up GitHub Actions for automated deployments
- **Monitoring**: Create CloudWatch dashboards
- **Scaling**: Adjust Lambda concurrency limits
- **Cost Optimization**: Review Bedrock pricing and optimize prompts

For more information, see:
- [ARCHITECTURE.md](ARCHITECTURE.md) - Deep dive into system design
- [API.md](API.md) - Data schemas and formats
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Solutions to common problems
