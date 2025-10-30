# Example Campaign Briefs

This folder contains sample campaign briefs to test the Creative Automation Service.

## Files

### `01-simple-nike.json` - Single Product, AI Generation
- **Use Case**: Simple campaign with one product
- **Strategy**: AI generates the product image from description
- **Cost**: ~$0.44 (1 generation + 5 variants)

### `02-multi-product-apple.json` - Multi-Product, Asset Reuse
- **Use Case**: Holiday campaign with 3 products
- **Strategy**: 2 products reuse existing assets, 1 generates new
- **Cost**: ~$0.46 (1 generation + 3×5 variants)
- **Note**: Demonstrates cost savings with asset reuse

### `03-hybrid-fashion.json` - Fashion Campaign, Mixed Strategy
- **Use Case**: Summer fashion collection with 4 products
- **Strategy**: 2 reuse existing assets, 2 generate new
- **Cost**: ~$0.92 (2 generations + 4×5 variants)

## Campaign Brief Schema

```json
{
  "campaign_name": "string (required)",
  "campaign_message": "string (required) - Main marketing message",
  "brand_colors": ["array of hex colors (optional)"],
  "target_regions": ["array of region codes (optional)"],
  "products": [
    {
      "name": "string (required)",
      "description": "string (required) - Used for AI generation",
      "existing_assets": "string (optional) - S3 path to reuse"
    }
  ]
}
```

## How to Use

1. **Customize a brief**: Copy one of these files and modify for your needs
2. **Upload to S3**:
   ```bash
   aws s3 cp examples/campaign-briefs/01-simple-nike.json \
     s3://YOUR-BUCKET-NAME/input/campaign-briefs/
   ```
3. **Monitor progress**:
   ```bash
   # Watch Lambda logs
   aws logs tail /aws/lambda/dev-creative-automation-parser --follow
   
   # Check manifest
   aws s3 cp s3://YOUR-BUCKET-NAME/output/CAMPAIGN-ID/manifest.json -
   ```

## Existing Assets Setup

If using `existing_assets`, organize your S3 bucket like this:

```
s3://YOUR-BUCKET/
├── existing-assets/
│   ├── apple/
│   │   ├── iphone-15-pro/
│   │   │   └── product.png
│   │   └── airpods-pro/
│   │       └── product.png
│   └── zara/
│       └── summer-2025/
│           ├── blazer/
│           │   └── product.png
│           └── accessories/
│               └── product.png
```

**Image Requirements**:
- Format: PNG or JPEG
- Resolution: 1024×1024 or higher
- Background: Transparent or white preferred
- File name: `product.png` (must be exact)

## Testing Tips

1. **Start simple**: Use `01-simple-nike.json` first to validate the pipeline
2. **Check costs**: Monitor CloudWatch metrics to understand actual costs
3. **Review outputs**: Download variants from `output/CAMPAIGN-ID/variants/`
4. **Iterate prompts**: Adjust product descriptions to improve AI generation quality

## Cost Examples

| Campaign | Products | Strategy | Total Cost |
|----------|----------|----------|------------|
| Nike (01) | 1 | All AI | $0.44 |
| Apple (02) | 3 | 2 reuse, 1 AI | $0.46 |
| Zara (03) | 4 | 2 reuse, 2 AI | $0.92 |

**Cost Breakdown**:
- AI Generation: $0.30/image (Bedrock Stable Diffusion XL)
- Asset Reuse: $0.01/image (S3 transfer only)
- Variants: $0.01/product (image processing)
- Total per product: $0.05 (variants processing)

## Troubleshooting

**"Asset not found" error**:
- Verify the `existing_assets` path matches your S3 structure
- Ensure the file is named `product.png` exactly
- Check S3 bucket permissions

**Poor AI generation quality**:
- Make product descriptions more detailed
- Include specific colors, materials, angles
- Avoid ambiguous terms

**Campaign not starting**:
- Check S3 event notification is configured
- Verify SQS queue is receiving messages
- Review parser Lambda CloudWatch logs
