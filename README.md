# Creative Automation Service 🎨

**Serverless AI-powered social media campaign generator using AWS Bedrock Titan**

Upload a campaign brief JSON → Get 5 platform-optimized images per product with branded overlays → Track costs automatically.

---

## 🎯 What It Does

1. **Upload** campaign brief (JSON) with product names and descriptions
2. **Generate** AI images using Amazon Bedrock Titan Image Generator ($0.04/image)
3. **Create** 5 social media variants with text overlays (Instagram, Facebook, Twitter, LinkedIn)
4. **Deliver** organized S3 output with complete cost tracking

**Cost**: ~$0.05 per product | **Time**: ~30 seconds per product

---

## 📋 Prerequisites

- **AWS Account** with Bedrock access
- **[AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)**
- **[Terraform](https://www.terraform.io/downloads)** (v1.5+)
- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)**
- **[Python 3.11+](https://www.python.org/downloads/)**

---

## 🚀 Quick Start

### 1. Enable Amazon Bedrock

```bash
# In AWS Console → Amazon Bedrock → Model Access
# Enable: amazon.titan-image-generator-v1
# Wait ~5 minutes for "Access granted" status
```

### 2. Configure AWS

```bash
aws configure
# AWS Access Key ID: <your-key>
# AWS Secret Access Key: <your-secret>
# Default region: us-east-1 (required for Bedrock)
# Default output format: json
```

### 3. Setup Project

```bash
git clone <your-repo-url>
cd creative-automation-service

# Edit terraform/environments/dev.tfvars
# Update: aws_account_id, s3_bucket_name (must be globally unique)
```

### 4. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform apply -var-file="environments/dev.tfvars" -auto-approve
# Creates: S3, SQS, Lambda (×3), ECR, IAM, CloudWatch
```

### 5. Build Lambda Functions

```bash
cd ..
./scripts/build-and-push.sh dev v1.0.0
# Builds and pushes 3 Docker containers to ECR (~5-10 mins)
```

### 6. Launch Dashboard

```bash
./run-dashboard.sh
# Opens Streamlit UI at http://localhost:8501
```

---

## 💡 How to Use

### Option 1: Dashboard UI (Recommended)

1. Open `http://localhost:8501`
2. Go to **"📝 Create Campaign"** tab
3. Upload JSON or use form builder
4. Click **"🚀 Launch Campaign"**
5. Track progress in **"📊 Track Progress"** tab
6. View results in **"🖼️ View Results"** tab

### Option 2: AWS CLI

```bash
# Upload campaign brief (auto-triggers pipeline)
aws s3 cp examples/campaign-briefs/01-simple-nike.json \
  s3://YOUR-BUCKET-NAME/input/campaign-briefs/
```

### Option 3: Example Campaigns

```bash
# Try Nike example (2 products)
aws s3 cp examples/campaign-briefs/01-simple-nike.json \
  s3://YOUR-BUCKET-NAME/input/campaign-briefs/

# Try French fashion example (4 products)
aws s3 cp examples/campaign-briefs/04-french-fashion.json \
  s3://YOUR-BUCKET-NAME/input/campaign-briefs/
```

---

## 📄 Campaign Brief Format

**Minimum Required:**

```json
{
  "campaign_name": "Spring Collection 2025",
  "campaign_message": "Fresh styles for the new season",
  "target_audience": "Fashion-conscious millennials aged 25-40",
  "target_regions": ["US", "CA"],
  "products": [
    {
      "name": "Summer Dress",
      "description": "Floral print midi dress with flowing fabric"
    },
    {
      "name": "Beach Sandals", 
      "description": "Comfortable leather sandals with arch support"
    }
  ]
}
```

**Optional Fields:**
- `brand_colors`: Array of hex colors (e.g., `["#FF6B35", "#FFFFFF"]`)
- `existing_asset_url`: S3 path to reuse existing images (saves $0.04/product)

**Minimum 2 products required per campaign**

See full examples in `examples/campaign-briefs/`

---

## 📂 Output Structure

```
s3://YOUR-BUCKET-NAME/output/
└── campaign-name-20251026-143022/
    ├── manifest.json                    # Status, costs, metadata
    ├── product-name-1/
    │   ├── generated/
    │   │   └── product-name-1-0.png    # AI-generated (1024×1024)
    │   └── aspect-ratios/
    │       ├── 1080x1080/instagram-square.jpg
    │       ├── 1080x1920/instagram-story.jpg
    │       ├── 1200x630/facebook-feed.jpg
    │       ├── 1200x675/twitter-card.jpg
    │       └── 1200x627/linkedin-post.jpg
    └── product-name-2/
        ├── generated/...
        └── aspect-ratios/...
```

**Each product generates:**
- 1 AI image (1024×1024 PNG)
- 5 social media variants (JPG with text overlays)

---

## 🏗️ Architecture

```
Campaign JSON Upload
        ↓
    S3 Bucket
        ↓ (Event Notification)
    SQS Queue
        ↓ (Trigger)
┌───────────────────┐
│ Lambda 1: Parser  │ Validates JSON, creates manifest
└────────┬──────────┘
         ↓
┌────────────────────┐
│ Lambda 2: Generator│ Calls Bedrock Titan, generates AI image
└────────┬───────────┘
         ↓
┌────────────────────┐
│ Lambda 3: Variants │ Creates 5 social media formats + overlays
└────────┬───────────┘
         ↓
    S3 Output Folder (campaign results)
```

**Lambda Functions:**

| Function | Purpose | Memory | Timeout | Cost |
|----------|---------|--------|---------|------|
| Parser | Validate JSON, create manifest | 512 MB | 300s | $0.0001 |
| Generator | Bedrock Titan image generation | 1024 MB | 120s | $0.04/image |
| Variants | Resize + overlay for 5 platforms | 2048 MB | 180s | $0.0011 |

**Total Cost per Product**: ~$0.05 (AI generation + processing + storage)

---

## 🎨 Design Decisions

### 1. Event-Driven Architecture
- **Why**: Auto-scales, decouples components, built-in retry logic
- **Trade-off**: Asynchronous (no immediate response)

### 2. Three-Lambda Pipeline
- **Why**: Single responsibility, independent scaling, better debugging
- **Trade-off**: Sequential processing (~30s per product)

### 3. Docker Containers
- **Why**: Large dependencies (PIL/Pillow >50MB), consistent environments
- **Trade-off**: Slower cold starts (~2s vs 200ms)

### 4. Amazon Bedrock Titan
- **Why**: AWS-native, no external APIs, IAM permissions, predictable costs
- **Trade-off**: us-east-1 only, 512-char prompt limit

### 5. Five Social Media Formats
- **Why**: Complete platform coverage, minimal additional cost
- **Trade-off**: More storage (5× per product)

---

## ⚠️ Assumptions & Limitations

### Assumptions
- Deployment in **us-east-1** (Bedrock Titan requirement)
- Bedrock model access **manually enabled** in console
- Campaign briefs follow **exact JSON schema**
- **Minimum 2 products** per campaign

### Limitations
- **Processing**: Sequential (~30s per product, not parallelized)
- **Resolution**: Max 1920×1080 (digital only, not print-quality)
- **Cold Starts**: First run after 15 min idle has ~3-5s delay
- **Prompt Length**: 512 characters max for Bedrock Titan
- **No Video**: Static images only (PNG/JPG)
- **Basic Fonts**: Default PIL fonts (no custom brand fonts)
- **Single Variation**: One image per product (no A/B testing)

---

## 🐛 Troubleshooting

### ❌ "AccessDenied: Bedrock model not accessible"
**Solution**: Enable Titan Image Generator in AWS Console → Bedrock → Model Access

### ❌ "S3 bucket already exists"
**Solution**: Change `s3_bucket_name` in `dev.tfvars` (must be globally unique)

### ❌ "Lambda timeout after 3 seconds"
**Solution**: Check Bedrock model access is enabled, verify IAM permissions

### ❌ "SSL certificate verify failed"
**Solution**: Corporate network issue - already fixed with `--no-verify-ssl` flags

### ❌ "Campaign stuck in 'processing' status"
**Check**:
```bash
# View Lambda logs
aws logs tail /aws/lambda/dev-creative-automation-generator --since 10m

# Check SQS queue
aws sqs get-queue-attributes \
  --queue-url <QUEUE_URL> \
  --attribute-names ApproximateNumberOfMessages
```

---

## 💰 Cost Breakdown

| Service | Usage | Cost per Campaign (2 products) |
|---------|-------|-------------------------------|
| **Bedrock Titan** | 2 images @ $0.04 each | $0.08 |
| **Lambda Execution** | 3 functions × 30s avg | $0.0012 |
| **S3 Storage** | ~12 images @ 2MB each | $0.0001/month |
| **SQS Messages** | 3 messages | $0.0000 |
| **CloudWatch Logs** | ~1MB logs | $0.0001 |
| **Total** | | **~$0.10** |

**Cost Optimization**:
- Use `existing_asset_url` to reuse images → Saves 97% ($0.01 vs $0.04)
- Batch campaigns to reduce cold starts
- Set CloudWatch log retention to 7 days

**Pricing Reference**: https://umbrellacost.com/blog/aws-bedrock-pricing/

---

## 🧹 Cleanup

```bash
# Destroy all infrastructure
cd terraform
terraform destroy -var-file="environments/dev.tfvars" -auto-approve

# Delete S3 bucket contents (required first)
aws s3 rm s3://YOUR-BUCKET-NAME --recursive

# Delete ECR images (optional)
aws ecr batch-delete-image \
  --repository-name creative-automation-parser \
  --image-ids "$(aws ecr list-images --repository-name creative-automation-parser --query 'imageIds[*]' --output json)"
```

---

## 📊 Monitoring

### View Logs

```bash
# Real-time logs for all functions
aws logs tail /aws/lambda/dev-creative-automation-parser --follow
aws logs tail /aws/lambda/dev-creative-automation-generator --follow  
aws logs tail /aws/lambda/dev-creative-automation-variants --follow

# Filter errors only
aws logs tail /aws/lambda/dev-creative-automation-generator \
  --filter-pattern "ERROR" --since 1h
```

### Check Queue Status

```bash
# Get queue depth
aws sqs get-queue-attributes \
  --queue-url <QUEUE_URL> \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible

# Check dead letter queue
aws sqs receive-message --queue-url <DLQ_URL> --max-number-of-messages 10
```

### Download Results

```bash
# List all campaigns
aws s3 ls s3://YOUR-BUCKET-NAME/output/

# Download specific campaign
aws s3 sync s3://YOUR-BUCKET-NAME/output/campaign-name-timestamp/ ./local/

# View manifest
cat ./local/manifest.json | jq
```

---

## 📁 Project Structure

```
creative-automation-service/
├── lambda/
│   ├── parser/         # Validates JSON, creates manifest
│   ├── generator/      # Bedrock Titan image generation
│   └── variants/       # Resizes + overlays for social media
├── terraform/          # Infrastructure as Code
│   ├── main.tf        # Main config
│   ├── s3.tf          # S3 bucket
│   ├── lambda.tf      # Lambda functions
│   ├── iam.tf         # IAM roles/policies
│   └── environments/
│       └── dev.tfvars # Environment config
├── scripts/
│   └── build-and-push.sh  # Docker build/deploy
├── examples/
│   └── campaign-briefs/   # Sample JSON files
├── app.py             # Streamlit dashboard
└── run-dashboard.sh   # Launch dashboard script
```

---

## 🎨 Streamlit Dashboard

For users who prefer a GUI over CLI:

```bash
./run-dashboard.sh
# Opens at http://localhost:8501
```

**Features**:
- 📊 **Overview**: Real-time metrics, campaign stats
- 📝 **Create Campaign**: Form builder + JSON upload
- 📊 **Track Progress**: Live Lambda logs, queue status
- 🖼️ **View Results**: Browse images, download variants

See **[STREAMLIT.md](STREAMLIT.md)** for complete dashboard guide.

---

## 📚 Additional Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Deep-dive into system design
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Detailed deployment guide
- **[TESTING-GUIDE.md](docs/TESTING-GUIDE.md)** - Testing strategies
- **[STREAMLIT.md](STREAMLIT.md)** - Dashboard user guide

---

## 🤝 Contributing

This is a portfolio project for interview purposes. Feel free to fork and adapt!

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Zoumana KEITA**
- AWS Solutions Architect Professional
- Portfolio Project: Adobe Firefly Principal Consultant Position
- October 2025

---

## 🔗 Resources

- **AWS Bedrock Pricing**: https://umbrellacost.com/blog/aws-bedrock-pricing/
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **Amazon Bedrock Docs**: https://docs.aws.amazon.com/bedrock/
- **Streamlit Docs**: https://docs.streamlit.io/

---

**Happy Automating! 🎨🤖**
