# End-to-End Testing Guide

Complete walkthrough to deploy and test the Creative Automation Service from scratch.

---

## Prerequisites Checklist

Before starting, verify you have:

- [ ] **AWS Account**: 385556511072
- [ ] **AWS CLI v2** installed and configured
- [ ] **Terraform ≥ 1.5** installed
- [ ] **Docker Desktop** running
- [ ] **Git** installed
- [ ] **PowerShell** (Windows) or Bash (Linux/Mac)

### Verify Installations

```powershell
# Run these commands in PowerShell
aws --version          # Should show: aws-cli/2.x.x
terraform --version    # Should show: Terraform v1.5+
docker --version       # Should show: Docker version 20.x+
git --version          # Should show: git version 2.x+

# Verify AWS credentials
aws sts get-caller-identity
# Should show Account: "385556511072"
```

---

## Step 1: Enable Amazon Bedrock (ONE-TIME SETUP)

**CRITICAL**: Without this step, image generation will fail.

### Option A: AWS Console (Recommended)
1. Open https://console.aws.amazon.com/bedrock/
2. **Important**: Switch region to **us-east-1** (top-right corner)
3. Click **Model access** in left sidebar
4. Click **Modify model access** button
5. Scroll to **Stability AI**
6. Check the box for **Stable Diffusion XL 1.0**
7. Click **Save changes** at bottom
8. Wait 2-3 minutes for status to show **Access granted** (green)

### Option B: AWS CLI
```powershell
# Request access to Stable Diffusion XL
aws bedrock put-model-invocation-logging-configuration `
  --region us-east-1 `
  --logging-config '{}'

# Verify access (wait 2-3 minutes, then run)
aws bedrock list-foundation-models `
  --region us-east-1 `
  --by-provider stability `
  --query 'modelSummaries[?contains(modelId, `stable-diffusion-xl`)].{ModelId:modelId,Status:modelLifecycle.status}'
```

**Expected output**:
```json
[
  {
    "ModelId": "stability.stable-diffusion-xl-v1",
    "Status": "ACTIVE"
  }
]
```

✅ **Verification**: You should see "ACTIVE" status.

---

## Step 2: Clone Project (if not already done)

```powershell
# Clone repository
cd "C:\Users\keitazo\OneDrive - Oxy\Desktop\PERSONAL\Job Application\Adobe Firefly"
cd creative-automation-service

# Verify structure
dir

# You should see:
# - lambda/
# - terraform/
# - scripts/
# - examples/
# - docs/
```

---

## Step 3: Build & Push Lambda Docker Images to ECR

This step builds 3 Docker containers and pushes them to ECR.

```powershell
# Make sure you're in the project root
cd "C:\Users\keitazo\OneDrive - Oxy\Desktop\PERSONAL\Job Application\Adobe Firefly\creative-automation-service"

# Run build script
.\scripts\build-and-push.ps1 dev
```

### What This Does:
1. Detects your AWS account (385556511072)
2. Authenticates Docker to ECR
3. Creates 3 ECR repositories:
   - `creative-automation-parser`
   - `creative-automation-generator`
   - `creative-automation-variants`
4. Builds Docker images from `lambda/*/Dockerfile`
5. Tags images with `latest` and timestamp
6. Pushes to ECR

**Expected Output**:
```
=====================================
 Creative Automation Service Builder
=====================================

Detecting AWS account...
AWS Account: 385556511072
AWS Region: us-east-1

Authenticating Docker to ECR...
Docker authenticated successfully

========================================
 Building: parser
========================================
Checking ECR repository: dev-creative-automation-parser
Building Docker image...
[+] Building 45.2s (8/8) FINISHED
Tagging image: latest, 20250123-143022
Pushing to ECR...
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

All Lambda images built and pushed to ECR.

Next steps:
  1. cd terraform
  2. terraform apply -var-file=environments/dev.tfvars
```

⏱️ **Time**: 5-10 minutes (depending on internet speed)

### Troubleshooting Build Issues

**Error: "Docker daemon not running"**
```powershell
# Start Docker Desktop and wait for it to be ready
# Then retry the build script
```

**Error: "Unable to locate credentials"**
```powershell
# Configure AWS CLI
aws configure
# Enter your access key, secret key, region (us-east-1), output (json)
```

**Error: "Access Denied to ECR"**
```powershell
# Re-authenticate Docker
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 385556511072.dkr.ecr.us-east-1.amazonaws.com
```

---

## Step 4: Deploy Infrastructure with Terraform

Now deploy all AWS resources (S3, SQS, Lambda, IAM, CloudWatch).

```powershell
# Navigate to terraform directory
cd terraform

# Initialize Terraform (first time only)
terraform init
```

**Expected output**:
```
Initializing the backend...
Initializing provider plugins...
- Finding latest version of hashicorp/aws...
- Installing hashicorp/aws v5.x.x...

Terraform has been successfully initialized!
```

### Preview Changes (Optional but Recommended)

```powershell
# See what will be created
terraform plan -var-file="environments/dev.tfvars"
```

**You should see**:
- **~20 resources** will be created
- S3 bucket, SQS queues, ECR repos, Lambda functions, IAM roles, CloudWatch logs

### Deploy Resources

```powershell
# Create all resources
terraform apply -var-file="environments/dev.tfvars"
```

Type `yes` when prompted.

**Expected output**:
```
Plan: 20 to add, 0 to change, 0 to destroy.

Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value: yes

...

Apply complete! Resources: 20 added, 0 changed, 0 destroyed.

Outputs:

campaign_bucket_name = "creative-automation-dev-keita-2025"

cloudwatch_log_groups = {
  "generator" = "/aws/lambda/dev-creative-automation-generator"
  "parser" = "/aws/lambda/dev-creative-automation-parser"
  "variants" = "/aws/lambda/dev-creative-automation-variants"
}

ecr_repository_urls = {
  "generator" = "385556511072.dkr.ecr.us-east-1.amazonaws.com/creative-automation-generator"
  "parser" = "385556511072.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser"
  "variants" = "385556511072.dkr.ecr.us-east-1.amazonaws.com/creative-automation-variants"
}

lambda_function_arns = {
  "generator" = "arn:aws:lambda:us-east-1:385556511072:function:dev-creative-automation-generator"
  "parser" = "arn:aws:lambda:us-east-1:385556511072:function:dev-creative-automation-parser"
  "variants" = "arn:aws:lambda:us-east-1:385556511072:function:dev-creative-automation-variants"
}

quick_start_commands = <<EOT
✅ Deployment complete!

S3 Bucket: creative-automation-dev-keita-2025

Next steps:
1. Upload a campaign brief:
   aws s3 cp examples/campaign-briefs/01-simple-nike.json s3://creative-automation-dev-keita-2025/input/campaign-briefs/

2. Monitor processing:
   aws logs tail /aws/lambda/dev-creative-automation-parser --follow

3. Check results:
   aws s3 ls s3://creative-automation-dev-keita-2025/output/ --recursive
EOT

sqs_dlq_url = "https://sqs.us-east-1.amazonaws.com/385556511072/dev-creative-automation-dlq"
sqs_queue_url = "https://sqs.us-east-1.amazonaws.com/385556511072/dev-creative-automation-queue"
```

⏱️ **Time**: 2-3 minutes

✅ **Success Indicator**: "Apply complete! Resources: 20 added"

---

## Step 5: Test with Simple Campaign (Single Product)

Let's test with the simplest example first.

### 5.1: Upload Campaign Brief

```powershell
# Go back to project root
cd ..

# Upload test campaign
aws s3 cp examples/campaign-briefs/01-simple-nike.json s3://creative-automation-dev-keita-2025/input/campaign-briefs/
```

**Expected output**:
```
upload: examples/campaign-briefs/01-simple-nike.json to s3://creative-automation-dev-keita-2025/input/campaign-briefs/01-simple-nike.json
```

### 5.2: Monitor Parser Lambda (Real-time)

Open a **new PowerShell window** and run:

```powershell
# Watch parser logs in real-time
aws logs tail /aws/lambda/dev-creative-automation-parser --follow --region us-east-1
```

**Expected logs** (within 10-30 seconds):
```
2025-01-23T14:30:22.123Z START RequestId: abc-123-def
2025-01-23T14:30:22.456Z INFO Received event: {"Records":[...]}
2025-01-23T14:30:23.111Z INFO Processing: s3://creative-automation-dev-keita-2025/input/campaign-briefs/01-simple-nike.json
2025-01-23T14:30:23.555Z INFO Saved manifest: s3://creative-automation-dev-keita-2025/output/nike-air-max-spring-launch-20250123-143023/manifest.json
2025-01-23T14:30:23.777Z INFO Generating new image for: Nike Air Max 270
2025-01-23T14:30:23.999Z END RequestId: abc-123-def
```

✅ **Success**: You see "Generating new image for: Nike Air Max 270"

### 5.3: Monitor Generator Lambda

Open **another PowerShell window** and run:

```powershell
# Watch generator logs
aws logs tail /aws/lambda/dev-creative-automation-generator --follow --region us-east-1
```

**Expected logs** (within 1-2 minutes):
```
2025-01-23T14:30:24.123Z START RequestId: xyz-789-abc
2025-01-23T14:30:24.456Z INFO Received event: {"campaign_id":"nike-air-max-spring-launch-20250123-143023",...}
2025-01-23T14:30:24.789Z INFO Calling Bedrock with prompt: Professional product photography of Nike Air Max 270...
2025-01-23T14:31:15.222Z INFO Saved image: s3://creative-automation-dev-keita-2025/output/nike-air-max-spring-launch-20250123-143023/generated/nike-air-max-270-0.png
2025-01-23T14:31:15.555Z END RequestId: xyz-789-abc
```

✅ **Success**: You see "Saved image: s3://..." and "Calling Bedrock"

⏱️ **Bedrock Generation Time**: ~30-60 seconds per image

### 5.4: Monitor Variants Lambda

Open **a third PowerShell window** and run:

```powershell
# Watch variants logs
aws logs tail /aws/lambda/dev-creative-automation-variants --follow --region us-east-1
```

**Expected logs** (within 2-3 minutes total):
```
2025-01-23T14:31:16.123Z START RequestId: def-456-ghi
2025-01-23T14:31:16.456Z INFO Received event: {"campaign_id":"nike-air-max-spring-launch-20250123-143023",...}
2025-01-23T14:31:18.111Z INFO Saved variant: instagram-square -> s3://.../variants/nike-air-max-270-0-instagram-square.jpg
2025-01-23T14:31:19.222Z INFO Saved variant: instagram-story -> s3://.../variants/nike-air-max-270-0-instagram-story.jpg
2025-01-23T14:31:20.333Z INFO Saved variant: facebook-feed -> s3://.../variants/nike-air-max-270-0-facebook-feed.jpg
2025-01-23T14:31:21.444Z INFO Saved variant: twitter-card -> s3://.../variants/nike-air-max-270-0-twitter-card.jpg
2025-01-23T14:31:22.555Z INFO Saved variant: linkedin-post -> s3://.../variants/nike-air-max-270-0-linkedin-post.jpg
2025-01-23T14:31:22.777Z INFO Generated 5 variants
2025-01-23T14:31:22.999Z END RequestId: def-456-ghi
```

✅ **Success**: You see "Generated 5 variants"

### 5.5: Check Campaign Results

```powershell
# List all output files
aws s3 ls s3://creative-automation-dev-keita-2025/output/ --recursive --human-readable
```

**Expected output**:
```
2025-01-23 14:30:23    1.2 KiB output/nike-air-max-spring-launch-20250123-143023/manifest.json
2025-01-23 14:31:15    2.4 MiB output/nike-air-max-spring-launch-20250123-143023/generated/nike-air-max-270-0.png
2025-01-23 14:31:18    856 KiB output/nike-air-max-spring-launch-20250123-143023/variants/nike-air-max-270-0-instagram-square.jpg
2025-01-23 14:31:19    1.1 MiB output/nike-air-max-spring-launch-20250123-143023/variants/nike-air-max-270-0-instagram-story.jpg
2025-01-23 14:31:20    742 KiB output/nike-air-max-spring-launch-20250123-143023/variants/nike-air-max-270-0-facebook-feed.jpg
2025-01-23 14:31:21    789 KiB output/nike-air-max-spring-launch-20250123-143023/variants/nike-air-max-270-0-twitter-card.jpg
2025-01-23 14:31:22    798 KiB output/nike-air-max-spring-launch-20250123-143023/variants/nike-air-max-270-0-linkedin-post.jpg
```

✅ **Success**: You see 1 manifest + 1 generated image + 5 variants = **7 files**

### 5.6: Download and View Manifest

```powershell
# Download manifest (replace CAMPAIGN-ID with actual ID from Step 5.5)
aws s3 cp s3://creative-automation-dev-keita-2025/output/nike-air-max-spring-launch-20250123-143023/manifest.json manifest.json

# View manifest
Get-Content manifest.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Expected manifest**:
```json
{
  "campaign_id": "nike-air-max-spring-launch-20250123-143023",
  "campaign_name": "Nike Air Max Spring Launch",
  "campaign_message": "Step into Spring with Comfort and Style",
  "brand_colors": ["#FF6B35", "#004E89", "#FFFFFF"],
  "target_regions": ["US", "CA", "UK"],
  "status": "completed",
  "created_at": "2025-01-23T14:30:23.123456",
  "completed_at": "2025-01-23T14:31:22.999999",
  "total_cost": 0.36,
  "products": [
    {
      "product_name": "Nike Air Max 270",
      "product_index": 0,
      "image_source": "generated",
      "generation_cost": 0.30,
      "processing_cost": 0.01,
      "variants_count": 5,
      "variants": [
        {
          "platform": "instagram-square",
          "key": "output/nike-air-max-spring-launch-20250123-143023/variants/nike-air-max-270-0-instagram-square.jpg"
        },
        {
          "platform": "instagram-story",
          "key": "output/nike-air-max-spring-launch-20250123-143023/variants/nike-air-max-270-0-instagram-story.jpg"
        },
        {
          "platform": "facebook-feed",
          "key": "output/nike-air-max-spring-launch-20250123-143023/variants/nike-air-max-270-0-facebook-feed.jpg"
        },
        {
          "platform": "twitter-card",
          "key": "output/nike-air-max-spring-launch-20250123-143023/variants/nike-air-max-270-0-twitter-card.jpg"
        },
        {
          "platform": "linkedin-post",
          "key": "output/nike-air-max-spring-launch-20250123-143023/variants/nike-air-max-270-0-linkedin-post.jpg"
        }
      ],
      "timestamp": "2025-01-23T14:31:15.555555",
      "completed_at": "2025-01-23T14:31:22.777777"
    }
  ]
}
```

✅ **Success Indicators**:
- `"status": "completed"`
- `"total_cost": 0.36` (reasonable)
- `"variants_count": 5`

### 5.7: Download All Images

```powershell
# Create local output folder
New-Item -ItemType Directory -Force -Path "test-output"

# Download all campaign outputs (replace CAMPAIGN-ID)
aws s3 sync s3://creative-automation-dev-keita-2025/output/nike-air-max-spring-launch-20250123-143023/ test-output/

# Open folder in Explorer
explorer test-output
```

**You should see**:
```
test-output/
├── manifest.json
├── generated/
│   └── nike-air-max-270-0.png         (1024x1024, AI-generated)
└── variants/
    ├── nike-air-max-270-0-instagram-square.jpg   (1080x1080)
    ├── nike-air-max-270-0-instagram-story.jpg    (1080x1920)
    ├── nike-air-max-270-0-facebook-feed.jpg      (1200x630)
    ├── nike-air-max-270-0-twitter-card.jpg       (1200x675)
    └── nike-air-max-270-0-linkedin-post.jpg      (1200x627)
```

✅ **Visual Verification**: Open the images and verify they look reasonable.

---

## Step 6: Test Multi-Product Campaign (Asset Reuse)

Now test a more complex scenario with 3 products.

### 6.1: Upload Apple Campaign

```powershell
aws s3 cp examples/campaign-briefs/02-multi-product-apple.json s3://creative-automation-dev-keita-2025/input/campaign-briefs/
```

### 6.2: Monitor All Logs

Use the same 3 PowerShell windows from Step 5 (they should still be running with `--follow`).

**Expected behavior**:
- Parser processes 3 products
- Generator is called **1 time** (Apple Watch Ultra - no existing asset)
- Variants is called **3 times** (all products)

⏱️ **Total Time**: ~3-4 minutes

### 6.3: Verify Results

```powershell
# List Apple campaign outputs (replace CAMPAIGN-ID)
aws s3 ls s3://creative-automation-dev-keita-2025/output/apple-holiday-tech-gift-guide-TIMESTAMP/ --recursive --human-readable
```

**Expected**:
- 1 manifest.json
- 1 generated image (Apple Watch)
- 15 variants (3 products × 5 platforms)
- **Note**: iPhone and AirPods will show errors (no existing assets uploaded yet)

---

## Step 7: Verify System Health

### 7.1: Check SQS Queue (Should be Empty)

```powershell
# Check main queue
aws sqs get-queue-attributes `
  --queue-url https://sqs.us-east-1.amazonaws.com/385556511072/dev-creative-automation-queue `
  --attribute-names ApproximateNumberOfMessages

# Expected output: "ApproximateNumberOfMessages": "0"
```

### 7.2: Check Dead Letter Queue (Should be Empty)

```powershell
# Check DLQ
aws sqs get-queue-attributes `
  --queue-url https://sqs.us-east-1.amazonaws.com/385556511072/dev-creative-automation-dlq `
  --attribute-names ApproximateNumberOfMessages

# Expected output: "ApproximateNumberOfMessages": "0"
```

✅ **Success**: Both queues are empty (no stuck/failed messages)

### 7.3: Check Lambda Metrics

```powershell
# Get invocation count for last hour
aws cloudwatch get-metric-statistics `
  --namespace AWS/Lambda `
  --metric-name Invocations `
  --dimensions Name=FunctionName,Value=dev-creative-automation-parser `
  --start-time (Get-Date).AddHours(-1).ToString("yyyy-MM-ddTHH:mm:ss") `
  --end-time (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss") `
  --period 3600 `
  --statistics Sum `
  --region us-east-1
```

**Expected**: You should see invocations matching your test campaigns.

---

## Step 8: Test Error Handling (Optional)

### 8.1: Upload Invalid Campaign Brief

```powershell
# Create invalid brief (missing required field)
@"
{
  "campaign_name": "Invalid Campaign"
}
"@ | Out-File -FilePath invalid-brief.json -Encoding utf8

# Upload
aws s3 cp invalid-brief.json s3://creative-automation-dev-keita-2025/input/campaign-briefs/
```

### 8.2: Verify Error Handling

```powershell
# Check parser logs for validation error
aws logs tail /aws/lambda/dev-creative-automation-parser --since 1m --region us-east-1
```

**Expected**: You should see "Invalid campaign brief: 'products' is a required property"

### 8.3: Check Dead Letter Queue

```powershell
# After 3 retries, message should be in DLQ
Start-Sleep -Seconds 30

aws sqs receive-message `
  --queue-url https://sqs.us-east-1.amazonaws.com/385556511072/dev-creative-automation-dlq
```

✅ **Success**: Failed message is captured in DLQ (not lost)

---

## Step 9: Cost Verification

### 9.1: Check Current Month Costs

```powershell
# Get cost breakdown (requires Cost Explorer enabled)
aws ce get-cost-and-usage `
  --time-period Start=2025-01-01,End=2025-01-31 `
  --granularity MONTHLY `
  --metrics BlendedCost `
  --group-by Type=SERVICE
```

### 9.2: Expected Costs (POC Testing)

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Bedrock | 2 images @ $0.04 each | $0.08 |
| Lambda | ~10 invocations, <1 min total | $0.00 (free tier) |
| S3 | ~20 MB storage | $0.00 (free tier) |
| ECR | 3 repos, ~1 GB storage | $0.10 |
| SQS | <10 messages | $0.00 (free tier) |
| CloudWatch | 3 log groups, minimal logs | $0.00 (free tier) |

**Total POC Cost**: ~**$0.20** for initial testing

---

## Step 10: Cleanup (When Done Testing)

⚠️ **WARNING**: This will delete all resources and data!

```powershell
# Navigate to terraform directory
cd terraform

# Destroy all resources
terraform destroy -var-file=environments/dev.tfvars
```

Type `yes` when prompted.

**This will delete**:
- All S3 bucket contents (campaigns, images)
- All Lambda functions
- ECR repositories and images
- SQS queues
- CloudWatch logs
- IAM roles

⏱️ **Time**: 2-3 minutes

---

## Troubleshooting

### Problem: "Bedrock AccessDeniedException"

**Solution**: Enable model access in Bedrock console (Step 1)

```powershell
# Verify model access
aws bedrock list-foundation-models --region us-east-1 --by-provider stability
```

### Problem: "S3 bucket already exists"

**Solution**: Bucket names must be globally unique. Edit `terraform/environments/dev.tfvars`:

```hcl
s3_bucket_name = "creative-automation-dev-keita-20250123"  # Add timestamp
```

Then re-run `terraform apply`.

### Problem: Lambda timeout (Generator)

**Symptom**: Generator logs show timeout after 2 minutes.

**Solution**: Increase timeout in `dev.tfvars`:

```hcl
lambda_generator_timeout = 180  # Increase to 3 minutes
```

Then re-deploy: `terraform apply -var-file=environments/dev.tfvars`

### Problem: No logs appearing

**Solution**: Check Lambda is actually running:

```powershell
# List recent Lambda invocations
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `dev-creative-automation`)].FunctionName'

# Check specific function
aws lambda get-function --function-name dev-creative-automation-parser
```

### Problem: Images look wrong

**Solution**: Adjust product descriptions in campaign brief. Be more specific:

```json
{
  "description": "White Nike Air Max 270 running shoe with visible blue Air unit, shot from 45-degree angle on white background, professional product photography, studio lighting"
}
```

---

## Success Criteria Checklist

After completing all steps, you should have:

- [x] **Bedrock enabled** for Stable Diffusion XL
- [x] **3 ECR repositories** created with Docker images
- [x] **20 AWS resources** deployed via Terraform
- [x] **Test campaign 1** (Nike) completed successfully
  - 1 generated image
  - 5 variants created
  - Manifest shows "completed" status
- [x] **Test campaign 2** (Apple) partially completed
  - 1 product generated, 2 failed (expected - no assets)
  - Errors logged correctly
- [x] **All logs visible** in CloudWatch
- [x] **SQS queues empty** (no stuck messages)
- [x] **DLQ captured errors** (invalid campaign)
- [x] **Total cost < $1** for testing

---

## Next Steps

1. **Upload existing assets** for campaign-briefs/02 and 03
2. **Customize prompts** in `lambda/generator/app.py`
3. **Add more variants** in `lambda/variants/app.py`
4. **Create custom campaigns** for your portfolio
5. **Document results** with screenshots for Adobe interview

---

## Quick Reference Commands

```powershell
# Upload campaign
aws s3 cp examples/campaign-briefs/01-simple-nike.json s3://creative-automation-dev-keita-2025/input/campaign-briefs/

# Watch logs
aws logs tail /aws/lambda/dev-creative-automation-parser --follow

# List outputs
aws s3 ls s3://creative-automation-dev-keita-2025/output/ --recursive --human-readable

# Download results
aws s3 sync s3://creative-automation-dev-keita-2025/output/CAMPAIGN-ID/ ./output/

# Check queue
aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/385556511072/dev-creative-automation-queue --attribute-names ApproximateNumberOfMessages

# Cleanup
terraform destroy -var-file=environments/dev.tfvars
```

---

**🎉 You're ready to test! Start with Step 1 and work through sequentially.**
