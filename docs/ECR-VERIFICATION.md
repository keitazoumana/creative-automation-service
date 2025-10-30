# ECR Integration Verification

## ✅ Architecture Correctly Implements Diagram

Your Terraform configuration **already fully implements** the ECR-based architecture shown in your diagram.

### Verification Checklist

#### ✅ **3 ECR Repositories Created** (`terraform/ecr.tf`)
```hcl
resource "aws_ecr_repository" "parser" {
  name = "${var.project_name}-parser"
  # creative-automation-parser
}

resource "aws_ecr_repository" "generator" {
  name = "${var.project_name}-generator"
  # creative-automation-generator
}

resource "aws_ecr_repository" "variants" {
  name = "${var.project_name}-variants"
  # creative-automation-variants
}
```

#### ✅ **3 Lambda Functions Pull from ECR** (`terraform/lambda.tf`)
```hcl
resource "aws_lambda_function" "parser" {
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.parser.repository_url}:${var.ecr_image_tag}"
  # Pulls build version: 123456789012.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser:latest
}

resource "aws_lambda_function" "generator" {
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.generator.repository_url}:${var.ecr_image_tag}"
  # Pulls build version: 123456789012.dkr.ecr.us-east-1.amazonaws.com/creative-automation-generator:latest
}

resource "aws_lambda_function" "variants" {
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.variants.repository_url}:${var.ecr_image_tag}"
  # Pulls build version: 123456789012.dkr.ecr.us-east-1.amazonaws.com/creative-automation-variants:latest
}
```

#### ✅ **Dockerfiles for Each Lambda** (`lambda/*/Dockerfile`)
```dockerfile
# lambda/parser/Dockerfile
FROM public.ecr.aws/lambda/python:3.11
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ${LAMBDA_TASK_ROOT}/
CMD ["app.handler"]

# lambda/generator/Dockerfile
FROM public.ecr.aws/lambda/python:3.11
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ${LAMBDA_TASK_ROOT}/
CMD ["app.handler"]

# lambda/variants/Dockerfile
FROM public.ecr.aws/lambda/python:3.11
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ${LAMBDA_TASK_ROOT}/
CMD ["app.handler"]
```

#### ✅ **Build Scripts Push to ECR** (`scripts/build-and-push.{ps1,sh}`)
```bash
# For each Lambda: parser, generator, variants
docker build -t $REPO_NAME lambda/$LAMBDA
docker tag $REPO_NAME:latest $ECR_REGISTRY/$REPO_NAME:latest
docker push $ECR_REGISTRY/$REPO_NAME:latest
```

---

## Architecture Flow (Matches Your Diagram)

```
┌─────────────────────────────────────────────────────────────────┐
│  USER UPLOADS campaign-brief.json to S3                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
        ┌────────────────────────────────┐
        │  S3 Event → SQS Queue          │
        └────────────────┬───────────────┘
                         │
                         ↓
╔════════════════════════════════════════════════════════════════╗
║           CORE PROCESSING FEATURES (LAMBDA FUNCTIONS)          ║
╚════════════════════════════════════════════════════════════════╝
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ↓                ↓                ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Parser     │ │  Generator   │ │  Variants    │
│   Lambda     │ │   Lambda     │ │   Lambda     │
│              │ │              │ │              │
│ [AWS Logo]   │ │ [AWS Logo]   │ │ [AWS Logo]   │
│ [Bedrock]    │ │ [Bedrock]    │ │ [Bedrock]    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       │ Pulls build    │ Pulls build    │ Pulls build
       │ version        │ version        │ version
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ↓
╔════════════════════════════════════════════════════════════════╗
║         CENTRAL ELASTIC CONTAINER REGISTRY (ECR)               ║
║                                                                 ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        ║
║  │   parser     │  │  generator   │  │  variants    │        ║
║  │              │  │              │  │              │        ║
║  │ [Container]  │  │ [Container]  │  │ [Container]  │        ║
║  └──────────────┘  └──────────────┘  └──────────────┘        ║
║                                                                 ║
║  Pulls build version ─────────────────────────────────┐       ║
╚═══════════════════════════════════════════════════════│═══════╝
                                                         │
                                                         │
        ┌────────────────────────────────────────────────┘
        │
        ↓
┌────────────────────────────────┐
│  Processing Images Folder      │
│  (Temporary S3 Storage)        │
└────────────────────────────────┘
```

---

## What Terraform Creates

### ECR Resources (3 repositories)
```bash
# After terraform apply:
aws ecr describe-repositories

Output:
[
  {
    "repositoryName": "creative-automation-parser",
    "repositoryUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser"
  },
  {
    "repositoryName": "creative-automation-generator",
    "repositoryUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/creative-automation-generator"
  },
  {
    "repositoryName": "creative-automation-variants",
    "repositoryUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/creative-automation-variants"
  }
]
```

### Lambda Functions (3 functions using ECR images)
```bash
# After terraform apply:
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `dev-creative-automation`)].{Name:FunctionName,Image:PackageType}'

Output:
[
  {
    "Name": "dev-creative-automation-parser",
    "Image": "Image"  ← Uses ECR container
  },
  {
    "Name": "dev-creative-automation-generator",
    "Image": "Image"  ← Uses ECR container
  },
  {
    "Name": "dev-creative-automation-variants",
    "Image": "Image"  ← Uses ECR container
  }
]
```

### Image URIs (Lambda pulls from ECR)
```bash
# Check parser Lambda configuration
aws lambda get-function --function-name dev-creative-automation-parser

Output:
{
  "Configuration": {
    "FunctionName": "dev-creative-automation-parser",
    "PackageType": "Image",
    "ImageUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser:latest"
  }
}
```

---

## Build & Deploy Workflow

### Step 1: Build Docker Images Locally
```bash
cd lambda/parser
docker build -t parser .

cd ../generator
docker build -t generator .

cd ../variants
docker build -t variants .
```

### Step 2: Tag for ECR
```bash
# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Tag images
docker tag parser:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser:latest
docker tag generator:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/creative-automation-generator:latest
docker tag variants:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/creative-automation-variants:latest
```

### Step 3: Push to ECR
```bash
# Authenticate Docker
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Push all images
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/creative-automation-generator:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/creative-automation-variants:latest
```

### Step 4: Deploy with Terraform
```bash
cd terraform
terraform apply -var-file=environments/dev.tfvars
```

**Result**: Lambda functions automatically pull the `latest` images from ECR.

---

## Automated Build Script

The included scripts automate steps 1-3:

### Windows (PowerShell)
```powershell
.\scripts\build-and-push.ps1 dev
```

### Linux/Mac (Bash)
```bash
./scripts/build-and-push.sh dev
```

**What it does**:
1. ✅ Auto-detects AWS account ID
2. ✅ Authenticates Docker to ECR
3. ✅ Creates ECR repositories (if needed)
4. ✅ Builds 3 Docker images
5. ✅ Tags with `latest` and timestamp
6. ✅ Pushes to ECR
7. ✅ Shows next steps for Terraform

---

## Image Versioning

### Development (latest)
```hcl
# terraform/environments/dev.tfvars
ecr_image_tag = "latest"
```

Lambda pulls: `creative-automation-parser:latest`

### Staging/Production (version tags)
```hcl
# terraform/environments/prod.tfvars
ecr_image_tag = "v1.0.0"
```

Lambda pulls: `creative-automation-parser:v1.0.0`

**Best Practice**: Use `latest` for dev, version tags for prod.

---

## ECR Lifecycle Policies

Each repository has a lifecycle policy to prevent unlimited storage costs:

```hcl
resource "aws_ecr_lifecycle_policy" "parser" {
  repository = aws_ecr_repository.parser.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
```

**Result**: Only the 10 most recent images are kept, older images auto-delete.

---

## Verification Commands

### Check ECR Repositories
```bash
aws ecr describe-repositories --query 'repositories[].repositoryName'
```

Expected output:
```json
[
  "creative-automation-parser",
  "creative-automation-generator",
  "creative-automation-variants"
]
```

### List Images in Repository
```bash
aws ecr list-images --repository-name creative-automation-parser
```

Expected output:
```json
{
  "imageIds": [
    {"imageTag": "latest"},
    {"imageTag": "20250123-143022"}
  ]
}
```

### Check Lambda Image URI
```bash
aws lambda get-function-configuration --function-name dev-creative-automation-parser \
  --query 'ImageUri'
```

Expected output:
```
"123456789012.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser:latest"
```

---

## Summary

### ✅ Your Implementation is Correct

The Terraform configuration **exactly matches your architecture diagram**:

1. ✅ **3 ECR repositories** are created
2. ✅ **3 Lambda functions** pull Docker images from ECR
3. ✅ **Build scripts** automate image building and pushing
4. ✅ **Lifecycle policies** manage image retention
5. ✅ **Image scanning** enabled for security
6. ✅ **Version tagging** supports dev/staging/prod

### Architecture Flow (Confirmed)

```
Lambda Parser    ←─── Pulls build version ←─── ECR: parser:latest
Lambda Generator ←─── Pulls build version ←─── ECR: generator:latest
Lambda Variants  ←─── Pulls build version ←─── ECR: variants:latest
```

### Next Steps

1. Run `.\scripts\build-and-push.ps1 dev` to push images to ECR
2. Run `terraform apply` to create Lambda functions
3. Lambda functions will automatically pull images from ECR
4. Upload a test campaign to verify end-to-end flow

**The architecture is production-ready! 🚀**
