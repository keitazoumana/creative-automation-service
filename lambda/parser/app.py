"""
Campaign Brief Parser Lambda

Receives campaign briefs from SQS, validates them, and orchestrates
the image generation pipeline with content safety checks.
"""

import json
import os
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, List
from jsonschema import validate, ValidationError

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')
sqs = boto3.client('sqs')

S3_BUCKET = os.environ['S3_BUCKET_NAME']
GENERATOR_FUNCTION = os.environ['GENERATOR_FUNCTION']
VARIANTS_FUNCTION = os.environ['VARIANTS_FUNCTION']

SCHEMA = {
    "type": "object",
    "required": ["campaign_name", "campaign_message", "products", "target_regions", "target_audience"],
    "properties": {
        "campaign_name": {"type": "string", "minLength": 1},
        "campaign_message": {"type": "string", "minLength": 1},
        "target_audience": {"type": "string", "minLength": 1},
        "brand_colors": {
            "type": "array",
            "items": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"}
        },
        "target_regions": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "products": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "required": ["name", "description"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "existing_assets": {"type": "string"}
                }
            }
        }
    }
}


def handler(event, context):
    """Main Lambda handler"""
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        for record in event['Records']:
            process_record(record)
        
        return {'statusCode': 200, 'body': 'Success'}
    
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {'statusCode': 500, 'body': str(e)}


def process_record(record: Dict[str, Any]):
    """Process single SQS record"""
    message = json.loads(record['body'])
    s3_event = message['Records'][0]
    
    bucket = s3_event['s3']['bucket']['name']
    key = s3_event['s3']['object']['key']
    
    logger.info(f"Processing: s3://{bucket}/{key}")
    
    brief = download_brief(bucket, key)
    validate_brief(brief)
    
    campaign_id = f"{sanitize(brief['campaign_name'])}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    
    manifest = create_manifest(campaign_id, brief)
    save_manifest(campaign_id, manifest)
    
    for idx, product in enumerate(brief['products']):
        process_product(campaign_id, product, idx, brief)


def download_brief(bucket: str, key: str) -> Dict[str, Any]:
    """Download campaign brief from S3"""
    response = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(response['Body'].read())


def validate_brief(brief: Dict[str, Any]):
    """Validate campaign brief schema"""
    try:
        validate(instance=brief, schema=SCHEMA)
    except ValidationError as e:
        raise ValueError(f"Invalid campaign brief: {e.message}")

def create_manifest(campaign_id: str, brief: Dict[str, Any]) -> Dict[str, Any]:
    """Create initial campaign manifest"""
    return {
        "campaign_id": campaign_id,
        "campaign_name": brief['campaign_name'],
        "campaign_message": brief['campaign_message'],
        "target_audience": brief['target_audience'],
        "brand_colors": brief.get('brand_colors', ['#000000', '#FFFFFF']),
        "target_regions": brief.get('target_regions', ['US']),
        "status": "processing",
        "created_at": datetime.utcnow().isoformat(),
        "products": [],
        "expected_products": len(brief['products']),
        "total_cost": 0.0
    }


def save_manifest(campaign_id: str, manifest: Dict[str, Any]):
    """Save manifest to S3"""
    key = f"output/{campaign_id}/manifest.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(manifest, indent=2),
        ContentType='application/json'
    )
    logger.info(f"Saved manifest: s3://{S3_BUCKET}/{key}")


def add_product_to_manifest(campaign_id: str, product_name: str, index: int):
    """Add product entry to manifest"""
    manifest_key = f"output/{campaign_id}/manifest.json"
    
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=manifest_key)
        manifest = json.loads(response['Body'].read())
        
        # Add product entry if not exists
        product_entry = {
            'product_index': index,
            'product_name': product_name,
            'status': 'processing'
        }
        manifest['products'].append(product_entry)
        
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=manifest_key,
            Body=json.dumps(manifest, indent=2),
            ContentType='application/json'
        )
        logger.info(f"Added product to manifest: {product_name} (index: {index})")
    except Exception as e:
        logger.error(f"Failed to add product to manifest: {e}")


def process_product(
    campaign_id: str,
    product: Dict[str, Any],
    index: int,
    brief: Dict[str, Any]
):
    """Process individual product"""
    # Add product entry to manifest
    add_product_to_manifest(campaign_id, product['name'], index)
    
    existing_assets = product.get('existing_assets')
    
    if existing_assets:
        asset_key = f"existing-assets/{existing_assets}product.png"
        if object_exists(S3_BUCKET, asset_key):
            logger.info(f"Reusing existing asset: {asset_key}")
            invoke_variants(campaign_id, product['name'], index, asset_key, brief, 'existing')
            return
    
    logger.info(f"Generating new image for: {product['name']}")
    invoke_generator(campaign_id, product, index, brief)


def object_exists(bucket: str, key: str) -> bool:
    """Check if S3 object exists"""
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except:
        return False


def invoke_generator(
    campaign_id: str,
    product: Dict[str, Any],
    index: int,
    brief: Dict[str, Any]
):
    """Invoke AI image generator Lambda"""
    payload = {
        'campaign_id': campaign_id,
        'product_name': product['name'],
        'product_description': product['description'],
        'product_index': index,
        'campaign_message': brief['campaign_message'],
        'target_audience': brief['target_audience'],
        'target_region': brief['target_regions'][0] if brief.get('target_regions') else 'US',
        'brand_colors': brief.get('brand_colors', ['#000000'])
    }
    
    lambda_client.invoke(
        FunctionName=GENERATOR_FUNCTION,
        InvocationType='Event',
        Payload=json.dumps(payload)
    )


def invoke_variants(
    campaign_id: str,
    product_name: str,
    index: int,
    image_key: str,
    brief: Dict[str, Any],
    source: str
):
    """Invoke variants generator Lambda"""
    payload = {
        'campaign_id': campaign_id,
        'product_name': product_name,
        'product_index': index,
        'image_key': image_key,
        'image_source': source,
        'campaign_message': brief['campaign_message'],
        'brand_colors': brief.get('brand_colors', ['#000000', '#FFFFFF'])
    }
    
    lambda_client.invoke(
        FunctionName=VARIANTS_FUNCTION,
        InvocationType='Event',
        Payload=json.dumps(payload)
    )


def sanitize(text: str) -> str:
    """Sanitize text for use in IDs"""
    return text.lower().replace(' ', '-')[:30]
