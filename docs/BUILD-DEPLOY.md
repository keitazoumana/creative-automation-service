hem# Build and Deployment Instructions (Bash)

## Prerequisites
- Bash shell (Git Bash on Windows, or native on Linux/Mac)
- AWS CLI configured
- Docker running
- Terraform installed

---

## Step 1: Make Script Executable

```bash
cd /c/Users/keitazo/OneDrive\ -\ Oxy/Desktop/PERSONAL/Job\ Application/Adobe\ Firefly/creative-automation-service
chmod +x scripts/build-and-push.sh
```

---

## Step 2: Build and Push Docker Images to ECR

### Option A: Development Build (with "latest" tag)
```bash
./scripts/build-and-push.sh dev latest
```

### Option B: Versioned Build (recommended)
```bash
./scripts/build-and-push.sh dev v1.0.0
```

### Option C: Production Build
```bash
./scripts/build-and-push.sh prod v1.0.0
```

---

## What the Script Does

1. **Detects AWS account** (385556511072)
2. **Authenticates Docker** to ECR
3. **Creates ECR repositories** (if they don't exist):
   - `creative-automation-parser`
   - `creative-automation-generator`
   - `creative-automation-variants`
4. **Builds Docker images** from `lambda/*/Dockerfile`
5. **Tags images** with three tags:
   - `latest` (always points to most recent)
   - `v1.0.0` (your specified version)
   - `v1.0.0-20250123-143022` (version + timestamp for traceability)
6. **Pushes all tags** to ECR

---

## Expected Output

```bash
=====================================
 Creative Automation Service Builder
=====================================

Environment: dev
Version: v1.0.0

Detecting AWS account...
AWS Account: 385556511072
AWS Region: us-east-1

Authenticating Docker to ECR...
Login Succeeded
Docker authenticated successfully

Build number: v1.0.0-20250123-143022

========================================
 Building: parser
========================================
Checking ECR repository: creative-automation-parser
Building Docker image...
[+] Building 45.2s (8/8) FINISHED
Tagging images:
  - latest
  - v1.0.0
  - v1.0.0-20250123-143022
Pushing to ECR...
The push refers to repository [385556511072.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser]
...
✓ Successfully pushed parser to ECR
  Image URI: 385556511072.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser:v1.0.0

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

Build Information:
  Environment: dev
  Version: v1.0.0
  Build Number: v1.0.0-20250123-143022
  ECR Registry: 385556511072.dkr.ecr.us-east-1.amazonaws.com

Images pushed:
  - 385556511072.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser:v1.0.0
  - 385556511072.dkr.ecr.us-east-1.amazonaws.com/creative-automation-generator:v1.0.0
  - 385556511072.dkr.ecr.us-east-1.amazonaws.com/creative-automation-variants:v1.0.0

Next steps:
  1. Update terraform/environments/dev.tfvars with:
     ecr_image_tag = "v1.0.0"

  2. Deploy infrastructure:
     cd terraform
     terraform apply -var-file=environments/dev.tfvars
```

---

## Step 3: Update Terraform Configuration

Edit `terraform/environments/dev.tfvars`:

```hcl
# Change this line to match your build version
ecr_image_tag = "v1.0.0"  # or "latest" for development
```

---

## Step 4: Deploy Infrastructure with Terraform

```bash
cd terraform

# Initialize (first time only)
terraform init

# Preview changes
terraform plan -var-file=environments/dev.tfvars

# Deploy (this should be FAST now that images exist)
terraform apply -var-file=environments/dev.tfvars
```

Type `yes` when prompted.

**Expected time**: 2-3 minutes (NOT 7+ minutes!)

---

## Troubleshooting

### Error: "permission denied: ./scripts/build-and-push.sh"
```bash
chmod +x scripts/build-and-push.sh
```

### Error: "Cannot connect to Docker daemon"
```bash
# Start Docker Desktop, then retry
docker ps
```

### Error: "Unable to locate credentials"
```bash
# Configure AWS CLI
aws configure
# Enter:
# - Access Key ID
# - Secret Access Key
# - Region: us-east-1
# - Output: json
```

### Error: "repository does not exist"
This is normal on first run - the script creates repositories automatically.

### Error: "denied: Your authorization token has expired"
```bash
# Re-authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  385556511072.dkr.ecr.us-east-1.amazonaws.com
```

---

## Verify Images in ECR

```bash
# List all repositories
aws ecr describe-repositories --region us-east-1

# List images in parser repository
aws ecr list-images \
  --repository-name creative-automation-parser \
  --region us-east-1

# Get image details
aws ecr describe-images \
  --repository-name creative-automation-parser \
  --region us-east-1
```

---

## Version Management Best Practices

### Development
```bash
./scripts/build-and-push.sh dev latest
```
- Use `latest` tag for rapid iteration
- Terraform always pulls newest code

### Staging
```bash
./scripts/build-and-push.sh staging v1.0.0-rc1
```
- Use release candidate versions
- Test before promoting to production

### Production
```bash
./scripts/build-and-push.sh prod v1.0.0
```
- Use semantic versioning (v1.0.0, v1.1.0, v2.0.0)
- **Never use `latest` in production**
- Allows rollback to previous versions

---

## Complete Workflow Example

```bash
# 1. Make script executable (one-time)
chmod +x scripts/build-and-push.sh

# 2. Build version 1.0.0
./scripts/build-and-push.sh dev v1.0.0

# 3. Update Terraform config
# Edit terraform/environments/dev.tfvars:
# ecr_image_tag = "v1.0.0"

# 4. Deploy infrastructure
cd terraform
terraform apply -var-file=environments/dev.tfvars

# 5. Test the system
cd ..
aws s3 cp examples/campaign-briefs/01-simple-nike.json \
  s3://creative-automation-dev-keita-2025/input/campaign-briefs/

# 6. Monitor logs
aws logs tail /aws/lambda/dev-creative-automation-parser --follow

# 7. Check results (after 2-3 minutes)
aws s3 ls s3://creative-automation-dev-keita-2025/output/ --recursive
```

---

## Updating Lambda Code

When you make changes to Lambda functions:

```bash
# 1. Make your code changes in lambda/*/app.py

# 2. Build new version
./scripts/build-and-push.sh dev v1.0.1

# 3. Update Terraform
# Edit terraform/environments/dev.tfvars:
# ecr_image_tag = "v1.0.1"

# 4. Redeploy (only updates Lambda functions, not entire infrastructure)
cd terraform
terraform apply -var-file=environments/dev.tfvars

# Lambda will automatically pull new image from ECR
```

---

## Quick Commands Reference

```bash
# Build and push
./scripts/build-and-push.sh dev v1.0.0

# Deploy infrastructure
cd terraform && terraform apply -var-file=environments/dev.tfvars

# Upload test campaign
aws s3 cp examples/campaign-briefs/01-simple-nike.json s3://creative-automation-dev-keita-2025/input/campaign-briefs/

# Watch logs
aws logs tail /aws/lambda/dev-creative-automation-parser --follow

# List outputs
aws s3 ls s3://creative-automation-dev-keita-2025/output/ --recursive

# Download results
aws s3 sync s3://creative-automation-dev-keita-2025/output/CAMPAIGN-ID/ ./output/

# Clean up
cd terraform && terraform destroy -var-file=environments/dev.tfvars
```

---

## About the 7+ Minute Terraform Hang

This is **NOT normal**. The issue is likely:

1. **Lambda functions are waiting for ECR images that don't exist**
2. **AWS API is timing out trying to find the images**
3. **Terraform is retrying in the background**

**Solution**: Always run `./scripts/build-and-push.sh` BEFORE `terraform apply`

Once images exist in ECR, Terraform should complete in 2-3 minutes.
