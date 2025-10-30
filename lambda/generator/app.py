"""
Image Generator Lambda Function

Generates product images using Amazon Bedrock Titan Image Generator.
"""

import json
import boto3
import base64
import os
import logging
import time
import random
from typing import Dict, Any
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")
bedrock_client = boto3.client("bedrock-runtime")

S3_BUCKET = os.environ["S3_BUCKET_NAME"]
VARIANTS_FUNCTION = os.environ["VARIANTS_FUNCTION"]
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.titan-image-generator-v1")

# Pricing for Amazon Titan Image Generator v1
# Model: amazon.titan-image-generator-v1 (Premium Quality, 1024x1024, >51 steps)
# Cost: $0.04 per image
# Reference: https://umbrellacost.com/blog/aws-bedrock-pricing/
COST_PER_IMAGE = 0.04

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(f"Generator Lambda triggered")
    logger.info(f"Event: {json.dumps(event, indent=2)}")
    
    try:
        campaign_id = event["campaign_id"]
        product_name = event["product_name"]
        product_description = event["product_description"]
        product_index = event.get("product_index", 0)
        campaign_message = event.get("campaign_message", "")
        target_audience = event.get("target_audience", "")
        target_region = event.get("target_region", "US")
        brand_colors = event.get("brand_colors", [])
        
        logger.info(f"Generating image for: {product_name} (campaign: {campaign_id})")
        
        if product_index > 0:
            stagger_delay = product_index * 3.0
            logger.info(f"Staggering request by {stagger_delay}s (product index: {product_index})")
            time.sleep(stagger_delay)
        
        prompt = build_prompt(
            product_name, 
            product_description, 
            campaign_message, 
            target_audience, 
            target_region
        )
        logger.info(f"Prompt: {prompt[:200]}...")
        
        image_data = generate_image(prompt)
        logger.info(f"Image generated: {len(image_data)} bytes")
        
        image_key = f"output/{campaign_id}/generated/{sanitize(product_name)}-{product_index}.png"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=image_key,
            Body=image_data,
            ContentType="image/png",
            Metadata={
                "campaign-id": encode_metadata(campaign_id),
                "product-name": encode_metadata(product_name),
                "product-index": str(product_index),
                "model": BEDROCK_MODEL_ID,
                "cost": str(COST_PER_IMAGE)
            }
        )
        logger.info(f"Saved image: s3://{S3_BUCKET}/{image_key}")
        
        update_manifest(campaign_id, product_name, product_index, image_key, COST_PER_IMAGE)
        
        variants_payload = {
            "campaign_id": campaign_id,
            "product_name": product_name,
            "product_index": product_index,
            "image_key": image_key,
            "image_source": "generated",
            "campaign_message": campaign_message,
            "brand_colors": brand_colors
        }
        
        lambda_client.invoke(
            FunctionName=VARIANTS_FUNCTION,
            InvocationType="Event",
            Payload=json.dumps(variants_payload)
        )
        
        logger.info(f"Invoked variants generator for {image_key}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "campaign_id": campaign_id,
                "product_name": product_name,
                "image_key": image_key,
                "cost": COST_PER_IMAGE
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing image generation: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def build_prompt(product_name: str, product_description: str, campaign_message: str, target_audience: str, target_region: str) -> str:
    MAX_PROMPT_LENGTH = 512
    
    base_style = "High-end commercial advertising, studio lighting, clean white background, photorealistic, 4K quality, centered composition."
    
    full_prompt = f"""Professional commercial product photography of {product_name}.

Product Details: {product_description}

Target Audience: {target_audience}
Target Market: {target_region}
Campaign Message: {campaign_message}

Style: {base_style}"""
    
    if len(full_prompt) <= MAX_PROMPT_LENGTH:
        return full_prompt
    
    prompt_without_audience = f"""Professional commercial product photography of {product_name}.

Product Details: {product_description}

Target Market: {target_region}
Campaign Message: {campaign_message}

Style: {base_style}"""
    
    if len(prompt_without_audience) <= MAX_PROMPT_LENGTH:
        logger.warning(f"Prompt too long ({len(full_prompt)} chars), removed target_audience")
        return prompt_without_audience
    
    minimal_prompt = f"""Professional product photography of {product_name}.

{product_description}

Style: {base_style}"""
    
    if len(minimal_prompt) <= MAX_PROMPT_LENGTH:
        logger.warning(f"Prompt too long ({len(full_prompt)} chars), using minimal version")
        return minimal_prompt
    
    truncated = minimal_prompt[:MAX_PROMPT_LENGTH]
    logger.warning(f"Prompt too long ({len(minimal_prompt)} chars), truncated to {MAX_PROMPT_LENGTH}")
    return truncated


def generate_image(prompt: str, max_retries: int = 6, base_delay: float = 5.0) -> bytes:
    logger.info(f"Calling Bedrock Titan with model: {BEDROCK_MODEL_ID}")
    
    request_body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": prompt},
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "quality": "premium",
            "height": 1024,
            "width": 1024,
            "cfgScale": 8.0,
            "seed": 0
        }
    }
    
    for attempt in range(max_retries):
        try:
            response = bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response["body"].read())
            base64_image = response_body["images"][0]
            image_data = base64.b64decode(base64_image)
            
            logger.info(f"Successfully generated image: {len(image_data)} bytes")
            return image_data
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code == 'ThrottlingException':
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 2)
                    logger.warning(f"Throttled by Bedrock (attempt {attempt + 1}/{max_retries}). Waiting {delay:.2f}s before retry...")
                    time.sleep(delay)
                else:
                    logger.error(f"Max retries ({max_retries}) exhausted for Bedrock API")
                    raise
            else:
                logger.error(f"Bedrock API error: {error_code} - {str(e)}")
                raise
                
        except Exception as e:
            logger.error(f"Unexpected error in image generation: {str(e)}", exc_info=True)
            raise
    
    raise Exception(f"Failed to generate image after {max_retries} attempts")

def update_manifest(campaign_id: str, product_name: str, product_index: int, image_key: str, cost: float):
    try:
        manifest_key = f"output/{campaign_id}/manifest.json"
        
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=manifest_key)
        manifest = json.loads(response["Body"].read())
        
        product_entry = {
            "name": product_name,
            "index": product_index,
            "image_key": image_key,
            "image_source": "generated",
            "cost": cost,
            "model": BEDROCK_MODEL_ID
        }
        
        manifest["products"].append(product_entry)
        manifest["total_cost"] = manifest.get("total_cost", 0.0) + cost
        
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=manifest_key,
            Body=json.dumps(manifest, indent=2),
            ContentType="application/json"
        )
        
        logger.info(f"Updated manifest: {manifest_key}")
        
    except Exception as e:
        logger.error(f"Failed to update manifest: {str(e)}", exc_info=True)


def sanitize(text: str) -> str:
    return text.lower().replace(" ", "-").replace("_", "-")[:30]


def encode_metadata(text: str) -> str:
    try:
        text.encode('ascii')
        return text
    except UnicodeEncodeError:
        import urllib.parse
        return urllib.parse.quote(text, safe='')
