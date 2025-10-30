# Architecture Overview

## System Design

The Creative Automation Service follows a serverless, event-driven architecture using AWS managed services.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CREATIVE AUTOMATION PIPELINE                      │
└─────────────────────────────────────────────────────────────────────┘

User Upload
    │
    ↓
┌────────────────┐
│  S3 Bucket     │  ← Campaign briefs uploaded here
│  /input/       │
└────────┬───────┘
         │ S3 Event Notification
         ↓
┌────────────────┐
│  SQS Queue     │  ← Decouples S3 from Lambda
│  + DLQ         │
└────────┬───────┘
         │ Event Source Mapping
         ↓
┌────────────────────────────────────────────────────────────────────┐
│                    LAMBDA FUNCTIONS (Containers)                    │
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐      │
│  │   Parser     │────▶│  Generator   │────▶│  Variants    │      │
│  │              │     │              │     │              │      │
│  │  • Validate  │     │  • Call      │     │  • Resize    │      │
│  │  • Route     │     │    Bedrock   │     │  • Overlay   │      │
│  │  • Manifest  │     │  • Save PNG  │     │  • 5 sizes   │      │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘      │
│         │                    │                    │               │
└─────────┼────────────────────┼────────────────────┼───────────────┘
          │                    │                    │
          │  Pull build version from ECR            │
          ↓                    ↓                    ↓
┌────────────────────────────────────────────────────────────────────┐
│              CENTRAL ELASTIC CONTAINER REGISTRY (ECR)               │
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐      │
│  │  parser:     │     │  generator:  │     │  variants:   │      │
│  │  latest      │     │  latest      │     │  latest      │      │
│  │  v1.0.0      │     │  v1.0.0      │     │  v1.0.0      │      │
│  └──────────────┘     └──────────────┘     └──────────────┘      │
│                                                                      │
│  Built from lambda/*/Dockerfile                                     │
└────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          └────────────────────┴────────────────────┘
                              │
                              ↓
                    ┌──────────────────┐
                    │  Amazon Bedrock  │  ← AI Image Generation
                    │  Stable Diff XL  │
                    └──────────────────┘
                              │
                              ↓
                    ┌──────────────────┐
                    │  S3 Bucket       │  ← Results stored here
                    │  /output/        │
                    │  /generated/     │
                    │  /variants/      │
                    └──────────────────┘
                              │
                              ↓
                    ┌──────────────────┐
                    │  CloudWatch      │  ← Monitoring & Logs
                    │  Logs + Alarms   │
                    └──────────────────┘
```

---

## Component Details

### 1. **S3 Bucket** (Campaign Storage)
- **Purpose**: Store campaign briefs, generated images, and variants
- **Structure**:
  ```
  s3://bucket-name/
  ├── input/
  │   └── campaign-briefs/           ← Upload JSON here
  │       └── my-campaign.json
  ├── existing-assets/               ← Optional: reusable assets
  │   └── brand/product/product.png
  └── output/
      └── campaign-id-timestamp/
          ├── manifest.json          ← Campaign results
          ├── generated/             ← AI-generated images
          │   └── product-0.png
          └── variants/              ← Multi-platform variants
              ├── product-0-instagram-square.jpg
              ├── product-0-instagram-story.jpg
              ├── product-0-facebook-feed.jpg
              ├── product-0-twitter-card.jpg
              └── product-0-linkedin-post.jpg
  ```
- **Features**:
  - Versioning enabled
  - AES-256 encryption
  - Event notification → SQS
  - 90-day lifecycle policy

### 2. **SQS Queue** (Decoupling Layer)
- **Purpose**: Decouple S3 events from Lambda, enable retry logic
- **Components**:
  - **Main Queue**: Receives S3 ObjectCreated events for `*.json` files
  - **Dead Letter Queue (DLQ)**: Captures failed messages after 3 retries
- **Configuration**:
  - Message retention: 4 days (main), 14 days (DLQ)
  - Visibility timeout: 5 minutes (matches parser timeout)
  - Long polling: 20 seconds

**Why SQS?**
- ✅ Retry logic (failed briefs don't get lost)
- ✅ Rate limiting (controls Lambda concurrency)
- ✅ DLQ for debugging (inspect failed campaigns)
- ✅ Decoupling (S3 and Lambda work independently)

### 3. **ECR Repositories** (Container Registry)
- **Purpose**: Store Docker images for Lambda functions
- **Repositories**:
  1. `creative-automation-parser` → Parser Lambda
  2. `creative-automation-generator` → Generator Lambda
  3. `creative-automation-variants` → Variants Lambda

- **Features**:
  - Image scanning on push (security)
  - Mutable tags (allows `latest`)
  - Lifecycle policy (keeps last 10 images)

- **Build Process**:
  ```bash
  # Build locally
  docker build -t parser lambda/parser/
  
  # Tag for ECR
  docker tag parser:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser:{image_tag}
  
  # Push to ECR
  docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/creative-automation-parser:{image_tag}
  ```

### 4. **Lambda Functions** (Core Processing)

#### **Lambda 1: Parser** (`lambda/parser/`)
- **Trigger**: SQS event source mapping
- **Responsibilities**:
  1. Download campaign brief from S3
  2. Validate JSON schema (jsonschema library)
  3. Create campaign ID and manifest
  4. Check if products have `existing_assets`
  5. Route to Generator (new image) or Variants (existing)
  
- **Configuration**:
  - Memory: 512 MB
  - Timeout: 5 minutes
  - Concurrency: 10
  - Container: `parser:latest` from ECR

- **Environment Variables**:
  ```bash
  S3_BUCKET_NAME=creative-automation-dev-bucket
  GENERATOR_FUNCTION=dev-creative-automation-generator
  VARIANTS_FUNCTION=dev-creative-automation-variants
  LOG_LEVEL=INFO
  ```

#### **Lambda 2: Generator** (`lambda/generator/`)
- **Trigger**: Invoked by Parser Lambda (async)
- **Responsibilities**:
  1. Build AI prompt from product description
  2. Call Amazon Bedrock (Stable Diffusion XL)
  3. Decode base64 image
  4. Save PNG to S3 `/output/campaign-id/generated/`
  5. Update manifest with cost ($0.30)
  6. Invoke Variants Lambda

- **Configuration**:
  - Memory: 1024 MB
  - Timeout: 2 minutes
  - Concurrency: 5 (Bedrock rate limits)
  - Container: `generator:latest` from ECR

- **Environment Variables**:
  ```bash
  S3_BUCKET_NAME=creative-automation-dev-bucket
  VARIANTS_FUNCTION=dev-creative-automation-variants
  BEDROCK_MODEL_ID=amazon.titan-image-generator-v1
  LOG_LEVEL=INFO
  ```

- **Bedrock Request**:
  ```json
  {
    "text_prompts": [{"text": "Professional product photography...", "weight": 1.0}],
    "cfg_scale": 7.0,
    "steps": 50,
    "width": 1024,
    "height": 1024,
    "samples": 1
  }
  ```

#### **Lambda 3: Variants** (`lambda/variants/`)
- **Trigger**: Invoked by Parser or Generator (async)
- **Responsibilities**:
  1. Download source image (generated or existing)
  2. Create 5 social media variants:
     - Instagram Square (1080×1080)
     - Instagram Story (1080×1920)
     - Facebook Feed (1200×630)
     - Twitter Card (1200×675)
     - LinkedIn Post (1200×627)
  3. Add text overlay (campaign message)
  4. Save JPEGs to S3 `/output/campaign-id/variants/`
  5. Update manifest (mark campaign complete)

- **Configuration**:
  - Memory: 2048 MB (image processing)
  - Timeout: 3 minutes
  - Concurrency: 10
  - Container: `variants:latest` from ECR

- **Environment Variables**:
  ```bash
  S3_BUCKET_NAME=creative-automation-dev-bucket
  LOG_LEVEL=INFO
  ```

### 5. **Amazon Bedrock** (AI Image Generation)
- **Model**: Stability AI Stable Diffusion XL v1
- **Region**: us-east-1 (required)
- **Pricing**: $0.04/image (1024×1024, 50 steps)
- **Setup**: Must enable model access in Bedrock console

**Prompt Engineering**:
```python
prompt = f"""Professional product photography of {product_name}.
{product_description}.
High quality, studio lighting, white background, commercial advertising style.
Marketing campaign: {campaign_message}.
Photorealistic, 4K quality, centered composition."""
```

### 6. **IAM Role** (Permissions)
Single role shared by all Lambda functions (least privilege):

```hcl
Permissions:
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents
- S3: GetObject, PutObject, DeleteObject, ListBucket
- SQS: ReceiveMessage, DeleteMessage, GetQueueAttributes
- Lambda: InvokeFunction (for chaining)
- Bedrock: InvokeModel (Stable Diffusion XL)
```

### 7. **CloudWatch** (Monitoring)
- **Log Groups**:
  - `/aws/lambda/dev-creative-automation-parser`
  - `/aws/lambda/dev-creative-automation-generator`
  - `/aws/lambda/dev-creative-automation-variants`
- **Retention**: 7 days (dev), 14 days (staging), 30 days (prod)
- **Alarm**: Triggers when messages appear in DLQ

---

## Data Flow

### Scenario 1: New Image Generation
```
1. User uploads campaign-brief.json to S3
2. S3 triggers event → SQS queue
3. Parser Lambda receives SQS message
4. Parser validates brief, creates manifest
5. Parser invokes Generator Lambda (async)
6. Generator calls Bedrock → generates image
7. Generator saves PNG to S3, updates manifest
8. Generator invokes Variants Lambda (async)
9. Variants downloads image, creates 5 sizes
10. Variants saves variants to S3, marks complete
11. User downloads manifest.json and variants
```

**Cost**: $0.30 (Bedrock) + $0.01 (processing) + $0.05 (variants) = **$0.36/product**

### Scenario 2: Existing Asset Reuse
```
1. User uploads campaign-brief.json with existing_assets
2. S3 → SQS → Parser Lambda
3. Parser checks S3 for existing-assets/path/product.png
4. Parser invokes Variants Lambda directly (skip Generator)
5. Variants downloads existing asset
6. Variants creates 5 sizes, saves to S3
7. Manifest shows image_source: "existing"
```

**Cost**: $0.01 (S3 transfer) + $0.05 (variants) = **$0.06/product**

**Savings**: 83% cheaper than generating new images!

---

## Infrastructure as Code

All resources defined in Terraform (`terraform/*.tf`):

```hcl
# Resource count per environment
- 1 S3 bucket (versioned, encrypted)
- 2 SQS queues (main + DLQ)
- 3 ECR repositories (parser, generator, variants)
- 3 Lambda functions (512MB, 1024MB, 2048MB)
- 1 IAM role + policy
- 3 CloudWatch log groups
- 1 CloudWatch alarm (DLQ)
- 1 Lambda event source mapping (SQS → Parser)

Total: ~20 resources
```

**Deployment**:
```bash
# Initialize
terraform init

# Plan (preview changes)
terraform plan -var-file=environments/dev.tfvars

# Apply (create resources)
terraform apply -var-file=environments/dev.tfvars

# Destroy (clean up)
terraform destroy -var-file=environments/dev.tfvars
```

---

## Scalability

### Current Limits (POC)
- **Parser**: 10 concurrent executions
- **Generator**: 5 concurrent (Bedrock rate limits)
- **Variants**: 10 concurrent

**Throughput**: ~15 campaigns/minute (900/hour)

### Production Scaling
To handle 10,000 campaigns/day:
1. Increase Lambda concurrency limits
2. Request Bedrock quota increase
3. Enable S3 Transfer Acceleration
4. Add DynamoDB for manifest (faster than S3)
5. Implement caching for duplicate products
6. Add CloudFront for variant delivery

---

## Cost Breakdown

### Monthly Costs (100 campaigns, 3 products each)

| Service | Usage | Cost |
|---------|-------|------|
| **S3** | 300 generated + 1500 variants (1.5 GB) | $0.03 |
| **Lambda** | Parser (300 invocations), Generator (300), Variants (300) | $2.10 |
| **Bedrock** | 300 images (1024×1024, 50 steps) | $12.00 |
| **ECR** | 3 repositories, 10 images each | $0.30 |
| **SQS** | 300 messages | $0.00 |
| **CloudWatch** | 3 log groups, 7-day retention | $0.50 |
| **Data Transfer** | S3 → Lambda → Bedrock | $0.10 |

**Total**: **~$15.03/month** for 100 campaigns

**Per Campaign**: **$0.15** (assuming 3 products, 2 reuse + 1 generate)

### Cost Optimization
1. **Asset Reuse**: $0.06 vs $0.36 (83% savings)
2. **Aggressive Caching**: Store popular products
3. **Lifecycle Policies**: Auto-delete old campaigns
4. **Reserved Concurrency**: Prevent runaway costs
5. **Bedrock Alternatives**: Consider cheaper models for drafts

---

## Security

### Data Protection
- ✅ S3 encryption at rest (AES-256)
- ✅ S3 block public access
- ✅ ECR image scanning
- ✅ IAM least privilege roles
- ✅ VPC endpoints (optional, for production)

### Secrets Management
- ✅ No hardcoded credentials
- ✅ IAM roles for Lambda (no access keys)
- ✅ Terraform state in S3 (encrypted)
- ✅ .gitignore prevents committing secrets

### Compliance
- Campaign data stored in single region
- 90-day auto-deletion policy
- CloudWatch audit logs

---

## Monitoring

### Key Metrics
1. **Lambda Duration**: Track processing time
2. **Lambda Errors**: Failed invocations
3. **SQS DLQ Depth**: Failed campaigns
4. **Bedrock Throttles**: Rate limit hits
5. **S3 Storage**: Cost tracking

### CloudWatch Dashboards
```bash
# Parser invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=dev-creative-automation-parser \
  --statistics Sum \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-31T23:59:59Z \
  --period 3600
```

### Alarms
- DLQ messages > 0 → SNS notification
- Lambda errors > 5 in 5 minutes → Page on-call
- Bedrock throttles > 10 → Slack alert

---

## Future Enhancements

### Phase 2 (Production)
- [ ] DynamoDB for manifests (faster queries)
- [ ] Step Functions for orchestration
- [ ] API Gateway for campaign submission
- [ ] Cognito for user authentication
- [ ] CloudFront for variant delivery
- [ ] EventBridge for scheduling

### Phase 3 (Advanced Features)
- [ ] Multi-region deployment
- [ ] A/B testing variants
- [ ] Cost prediction before generation
- [ ] Product recommendation (ML)
- [ ] Video generation (Bedrock Titan)
- [ ] Localization (multi-language)

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

**Quick Checks**:
```bash
# Check Lambda logs
aws logs tail /aws/lambda/dev-creative-automation-parser --follow

# Check SQS queue depth
aws sqs get-queue-attributes \
  --queue-url YOUR-QUEUE-URL \
  --attribute-names ApproximateNumberOfMessages

# Check DLQ
aws sqs receive-message --queue-url YOUR-DLQ-URL

# List campaign outputs
aws s3 ls s3://YOUR-BUCKET/output/ --recursive
```

---

## References

- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [Amazon Bedrock](https://docs.aws.amazon.com/bedrock/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Stable Diffusion XL](https://stability.ai/stable-diffusion)
- [Docker for Lambda](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
