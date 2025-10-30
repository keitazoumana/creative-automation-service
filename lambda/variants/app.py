"""
Campaign Variants Generator Lambda

Creates multiple size/format variants from product images.
"""

import json
import os
import boto3
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

s3 = boto3.client('s3')
S3_BUCKET = os.environ['S3_BUCKET_NAME']

# Variant sizes (social media platforms)
VARIANTS = {
    'instagram-square': (1080, 1080),
    'instagram-story': (1080, 1920),
    'facebook-feed': (1200, 630),
    'twitter-card': (1200, 675),
    'linkedin-post': (1200, 627)
}


def handler(event, context):
    """Main Lambda handler"""
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        campaign_id = event['campaign_id']
        product_name = event['product_name']
        product_index = event['product_index']
        image_key = event['image_key']
        source = event['image_source']
        message = event['campaign_message']
        colors = event['brand_colors']
        
        # Download source image
        image_data = download_image(image_key)
        image = Image.open(BytesIO(image_data))
        
        # Generate all variants
        variant_keys = []
        for variant_name, size in VARIANTS.items():
            key = generate_variant(campaign_id, product_name, product_index, image, variant_name, size, message, colors)
            variant_keys.append({'platform': variant_name, 'key': key})
        
        # Update manifest with processing cost
        # AI generation: $0.04 (Titan Image Generator) + $0.01 (variant processing) = $0.05
        # Existing assets: $0.01 (variant processing only)
        # Reference: https://umbrellacost.com/blog/aws-bedrock-pricing/
        cost = 0.01 if source == 'existing' else 0.05
        update_manifest(campaign_id, product_name, product_index, variant_keys, source, cost)
        
        logger.info(f"Generated {len(variant_keys)} variants")
        return {'statusCode': 200, 'variants': len(variant_keys)}
    
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {'statusCode': 500, 'error': str(e)}


def download_image(key: str) -> bytes:
    """Download image from S3"""
    response = s3.get_object(Bucket=S3_BUCKET, Key=key)
    return response['Body'].read()


def generate_variant(
    campaign_id: str,
    product_name: str,
    index: int,
    image: Image.Image,
    variant_name: str,
    size: tuple,
    message: str,
    colors: list
) -> str:
    """Generate single variant"""
    
    # Create canvas
    canvas = Image.new('RGB', size, color=colors[0] if colors else '#FFFFFF')
    
    # Calculate image placement (centered)
    img_ratio = image.width / image.height
    canvas_ratio = size[0] / size[1]
    
    if img_ratio > canvas_ratio:
        # Image wider than canvas - fit width
        new_width = int(size[0] * 0.8)
        new_height = int(new_width / img_ratio)
    else:
        # Image taller than canvas - fit height
        new_height = int(size[1] * 0.7)
        new_width = int(new_height * img_ratio)
    
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Center image
    x = (size[0] - new_width) // 2
    y = (size[1] - new_height) // 2 - 50  # Slightly above center
    
    canvas.paste(resized, (x, y))
    
    # Add text overlay (simplified - in production use proper fonts)
    draw = ImageDraw.Draw(canvas)
    text = message[:50]  # Truncate long messages
    
    # Draw text at bottom (simplified - use ImageFont for better rendering)
    text_y = size[1] - 100
    bbox = draw.textbbox((0, 0), text)
    text_width = bbox[2] - bbox[0]
    text_x = (size[0] - text_width) // 2
    
    # Simple text shadow
    shadow_color = '#000000' if colors and colors[0] != '#000000' else '#FFFFFF'
    draw.text((text_x + 2, text_y + 2), text, fill=shadow_color)
    draw.text((text_x, text_y), text, fill='#FFFFFF')
    
    sanitized = product_name.lower().replace(' ', '-')[:30]
    aspect_ratio = f"{size[0]}x{size[1]}"
    key = f"output/{campaign_id}/{sanitized}/aspect-ratios/{aspect_ratio}/{variant_name}.jpg"
    
    buffer = BytesIO()
    canvas.save(buffer, format='JPEG', quality=90)
    
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=buffer.getvalue(),
        ContentType='image/jpeg'
    )
    
    logger.info(f"Saved variant: {variant_name} -> s3://{S3_BUCKET}/{key}")
    return key


def update_manifest(campaign_id: str, product_name: str, index: int, variants: list, source: str, cost: float):
    """Update campaign manifest with variants"""
    manifest_key = f"output/{campaign_id}/manifest.json"
    
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=manifest_key)
        manifest = json.loads(response['Body'].read())
        
        logger.info(f"Manifest has {len(manifest['products'])} products")
        
        # Find product entry
        product_found = False
        for product in manifest['products']:
            logger.info(f"Checking product: index={product.get('index', product.get('product_index'))}, name={product.get('product_name')}")
            if product.get('index') == index or product.get('product_index') == index:
                product['variants'] = variants
                product['variants_count'] = len(variants)
                product['processing_cost'] = cost
                product['completed_at'] = datetime.now(timezone.utc).isoformat()
                product['status'] = 'completed'
                product_found = True
                logger.info(f"Updated product at index {index} with {len(variants)} variants")
                break
        
        if not product_found:
            logger.error(f"Product not found in manifest: index={index}, name={product_name}")
            logger.error(f"Available products: {manifest['products']}")
            return
        
        manifest['total_cost'] += cost
        
        # Check if all products complete (each product should have variants)
        products_with_variants = sum(1 for p in manifest['products'] if 'variants' in p)
        expected_products = manifest.get('expected_products', len(manifest['products']))
        
        logger.info(f"Products with variants: {products_with_variants}/{expected_products}")
        
        if products_with_variants == expected_products:
            manifest['status'] = 'completed'
            manifest['completed_at'] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Campaign {campaign_id} completed!")
        
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=manifest_key,
            Body=json.dumps(manifest, indent=2),
            ContentType='application/json'
        )
        logger.info(f"Manifest updated successfully")
    except Exception as e:
        logger.error(f"Failed to update manifest: {e}", exc_info=True)
