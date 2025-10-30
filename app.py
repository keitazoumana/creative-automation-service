"""
Creative Automation Service - Streamlit Dashboard

A web interface for managing AI-powered social media campaign generation.
"""

import streamlit as st
import boto3
import json
import os
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
import pandas as pd
import time

# Page configuration
st.set_page_config(
    page_title="Campaign Creator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #FF6B35 0%, #004E89 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #FF6B35;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stButton>button {
        background: linear-gradient(90deg, #FF6B35 0%, #004E89 100%);
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize AWS clients
@st.cache_resource
def get_aws_clients():
    """Initialize and cache AWS clients with SSL verification disabled for corporate networks"""
    import botocore
    
    # Disable SSL verification for corporate networks with self-signed certificates
    config = botocore.config.Config(
        signature_version='s3v4',
        retries={'max_attempts': 3, 'mode': 'standard'}
    )
    
    return {
        's3': boto3.client('s3', verify=False, config=config),
        'logs': boto3.client('logs', verify=False, config=config),
        'lambda': boto3.client('lambda', verify=False, config=config),
        'sqs': boto3.client('sqs', verify=False, config=config)
    }

# Suppress SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

clients = get_aws_clients()

# Configuration
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'creative-automation-dev-keita-2025')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'creative-automation')

# Main header
st.markdown('<h1 class="main-header">🎨 Campaign Creator</h1>', unsafe_allow_html=True)
st.markdown("**Create Professional Social Media Campaigns in Minutes**")

# Sidebar navigation
st.sidebar.title("Menu")
page = st.sidebar.radio(
    "Choose a section",
    ["🏠 Overview", "📝 Create Campaign", "📊 Track Progress", "🖼️ View Results"]
)

# ==================== PAGE: OVERVIEW ====================
if page == "🏠 Overview":
    st.header("Campaign Overview")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try:
            # Count campaign briefs
            response = clients['s3'].list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix='input/campaign-briefs/'
            )
            contents = response.get('Contents', [])
            # Count only actual JSON files, not folder markers
            total_briefs = sum(1 for obj in contents if obj['Key'].endswith('.json'))
            st.metric("Campaigns Created", total_briefs)
        except:
            st.metric("Campaigns Created", 0)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try:
            # Count generated images
            response = clients['s3'].list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix='output/',
                Delimiter='/'
            )
            total_outputs = len(response.get('CommonPrefixes', []))
            st.metric("Campaigns Ready", total_outputs)
        except:
            st.metric("Campaigns Ready", "N/A")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try:
            # Calculate total cost from manifests
            response = clients['s3'].list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix='output/'
            )
            total_cost = 0.0
            for obj in response.get('Contents', []):
                if 'manifest.json' in obj['Key']:
                    try:
                        manifest_obj = clients['s3'].get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
                        manifest = json.loads(manifest_obj['Body'].read())
                        total_cost += manifest.get('total_cost', 0.0)
                    except:
                        pass
            st.metric("Total Investment", f"${total_cost:.2f}")
        except:
            st.metric("Total Investment", "$0.00")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try:
            # Count total variants
            response = clients['s3'].list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix='output/'
            )
            total_variants = sum(1 for obj in response.get('Contents', []) if 'variants/' in obj['Key'])
            st.metric("Images Generated", total_variants)
        except:
            st.metric("Images Generated", "N/A")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # Recent campaigns
    st.subheader("📋 Your Recent Campaigns")
    
    try:
        # List recent campaign outputs
        response = clients['s3'].list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix='output/',
            Delimiter='/'
        )
        
        campaigns = []
        for prefix in response.get('CommonPrefixes', [])[:10]:
            campaign_id = prefix['Prefix'].split('/')[-2]
            
            # Try to get manifest
            try:
                manifest_obj = clients['s3'].get_object(
                    Bucket=BUCKET_NAME,
                    Key=f"{prefix['Prefix']}manifest.json"
                )
                manifest = json.loads(manifest_obj['Body'].read())
                
                # Count unique products by using expected_products or counting those with variants
                product_count = manifest.get('expected_products', 0)
                if product_count == 0:
                    # Fallback: count unique products with variants
                    product_count = sum(1 for p in manifest.get('products', []) if 'variants' in p)
                
                status_display = "✅ Ready" if manifest.get('status') == 'completed' else "⏳ Processing"
                campaigns.append({
                    'Campaign Name': manifest.get('campaign_name', 'N/A'),
                    'Products': product_count,
                    'Status': status_display,
                    'Investment': f"${manifest.get('total_cost', 0.0):.2f}",
                    'Created': manifest.get('created_at', 'N/A')[:19]
                })
            except:
                campaigns.append({
                    'Campaign Name': campaign_id,
                    'Products': 0,
                    'Status': '⏳ Processing',
                    'Investment': '$0.00',
                    'Created': 'N/A'
                })
        
        if campaigns:
            df = pd.DataFrame(campaigns)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("🚀 Ready to get started? Create your first campaign and watch the magic happen!")
    
    except Exception as e:
        st.error("We're having trouble loading your campaigns right now. Please refresh the page or contact support.")
    
    st.divider()
    
    # System status
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("� System Status")
        try:
            # Check Lambda functions
            functions = [
                f"{ENVIRONMENT}-{PROJECT_NAME}-parser",
                f"{ENVIRONMENT}-{PROJECT_NAME}-generator",
                f"{ENVIRONMENT}-{PROJECT_NAME}-variants"
            ]
            
            active_count = 0
            for func_name in functions:
                try:
                    response = clients['lambda'].get_function(FunctionName=func_name)
                    active_count += 1
                except:
                    pass
            
            if active_count == len(functions):
                st.success("✅ All systems operational")
            else:
                st.warning("⚠️ Some services are offline")
        except Exception as e:
            st.error("❌ System check unavailable")
    
    with col2:
        st.subheader("� Storage Status")
        try:
            # Check S3 bucket
            clients['s3'].head_bucket(Bucket=BUCKET_NAME)
            st.success("✅ Storage connected")
            
            # Get bucket size
            response = clients['s3'].list_objects_v2(Bucket=BUCKET_NAME)
            total_size = sum(obj['Size'] for obj in response.get('Contents', []))
            st.info(f"📊 Space Used: {total_size / (1024**2):.1f} MB")
        except Exception as e:
            st.error("❌ Storage connection issue")

# ==================== PAGE: CREATE CAMPAIGN ====================
elif page == "📝 Create Campaign":
    st.header("Create New Campaign")
    
    st.markdown('<div class="info-box">💡 <strong>Let\'s get started!</strong> Fill out your campaign details below, or upload a file if you have one ready.</div>', unsafe_allow_html=True)
    
    # Tab interface
    tab1, tab2, tab3 = st.tabs(["📝 Campaign Builder", "📄 Upload File", "📚 Examples"])
    
    with tab1:
        st.subheader("Campaign Details (For Future Release)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            campaign_name = st.text_input("Campaign Name *", placeholder="e.g., Summer Collection 2025")
            campaign_message = st.text_area("Main Message *", placeholder="e.g., Step into summer with style and comfort")
        
        with col2:
            target_regions = st.multiselect(
                "Target Markets",
                ["US", "CA", "UK", "EU", "AU", "JP", "CN", "IN", "BR", "MX"],
                default=["US"],
                help="Choose which countries/regions this campaign will run in"
            )
            target_audience = st.text_input("Target Audience *", placeholder="e.g., Active professionals aged 25-40")
            brand_colors = st.text_input("Brand Colors (optional)", placeholder="#FF6B35, #004E89", help="Enter hex color codes separated by commas")
        
        st.divider()
        
        # Product details
        st.subheader("Your Products")
        st.write("Tell us about the products you want to feature in this campaign.")
        num_products = st.number_input("How many products?", min_value=2, max_value=10, value=2, help="Campaigns must include at least 2 products")
        
        products = []
        for i in range(num_products):
            with st.expander(f"Product {i+1}", expanded=(i==0)):
                p_name = st.text_input(f"Product Name *", key=f"p_name_{i}", placeholder="e.g., Nike Air Max 270")
                p_desc = st.text_area(
                    f"Product Description *",
                    key=f"p_desc_{i}",
                    placeholder="e.g., Premium running shoe with visible Air unit and all-day comfort",
                    help="Describe the key features and benefits of this product"
                )
                p_existing = st.text_input(
                    f"Use Existing Image (optional)",
                    key=f"p_exist_{i}",
                    placeholder="e.g., assets/nike-air-max.jpg",
                    help="If you already have a product image, enter the file path here. Otherwise, we'll create one for you!"
                )
                
                if p_name and p_desc:
                    product = {
                        "name": p_name,
                        "description": p_desc
                    }
                    if p_existing:
                        product["existing_asset_url"] = p_existing
                    products.append(product)
        
        st.divider()
        
        # Generate campaign JSON
        if st.button("🚀 Launch Campaign", type="primary", key="launch_from_form"):
            if not campaign_name or not campaign_message or not target_audience or len(products) == 0:
                st.error("⚠️ Please fill in all required fields marked with (*)")
            else:
                # Build campaign brief
                brief = {
                    "campaign_name": campaign_name,
                    "campaign_message": campaign_message,
                    "target_audience": target_audience,
                    "target_regions": target_regions,
                    "products": products
                }
                
                if brand_colors:
                    colors = [c.strip() for c in brand_colors.split(',')]
                    brief["brand_colors"] = colors
                
                # Upload to S3
                try:
                    filename = f"{campaign_name.lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
                    key = f"input/campaign-briefs/{filename}"
                    
                    clients['s3'].put_object(
                        Bucket=BUCKET_NAME,
                        Key=key,
                        Body=json.dumps(brief, indent=2),
                        ContentType='application/json'
                    )
                    
                    st.markdown(f'<div class="success-box">✅ <strong>Campaign created successfully!</strong><br>File: {filename}<br>S3: s3://{BUCKET_NAME}/{key}</div>', unsafe_allow_html=True)
                    
                    # Show JSON preview
                    with st.expander("📄 View Campaign Brief JSON"):
                        st.json(brief)
                    
                    st.info("🔄 Campaign is now processing. Check the 'Monitor Pipeline' page for status.")
                
                except Exception as e:
                    st.markdown(f'<div class="error-box">❌ <strong>Error:</strong> {str(e)}</div>', unsafe_allow_html=True)
    
    with tab2:
        st.subheader("Upload Campaign JSON")
        
        uploaded_file = st.file_uploader("Choose a JSON file", type=['json'])
        
        if uploaded_file:
            try:
                # Parse JSON
                brief = json.load(uploaded_file)
                
                # Validate schema
                required_fields = ['campaign_name', 'campaign_message', 'products']
                missing = [f for f in required_fields if f not in brief]
                
                if missing:
                    st.error(f"❌ Missing required fields: {', '.join(missing)}")
                else:
                    # Show preview
                    st.success("✅ Valid campaign brief")
                    with st.expander("📄 Preview JSON"):
                        st.json(brief)
                    
                    if st.button("🚀 Launch Campaign", type="primary", key="launch_from_upload"):
                        try:
                            filename = f"{brief['campaign_name'].lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
                            key = f"input/campaign-briefs/{filename}"
                            
                            clients['s3'].put_object(
                                Bucket=BUCKET_NAME,
                                Key=key,
                                Body=json.dumps(brief, indent=2),
                                ContentType='application/json'
                            )
                            
                            st.markdown(f'<div class="success-box">🎉 <strong>Campaign launched successfully!</strong><br>Your campaign is now being processed. Check the "Track Progress" section to see updates.</div>', unsafe_allow_html=True)
                        
                        except Exception as e:
                            st.markdown(f'<div class="error-box">❌ <strong>Something went wrong:</strong> Unable to launch campaign. Please try again or contact support.</div>', unsafe_allow_html=True)
            
            except json.JSONDecodeError:
                st.error("❌ The uploaded file doesn't appear to be in the correct format. Please check your file and try again.")
    
    with tab3:
        st.subheader("Campaign Templates")
        st.write("Get inspired by these sample campaigns, or use them as starting points for your own.")
        
        examples = {
            "Athletic Footwear Campaign": {
                "campaign_name": "Nike Air Max Spring Launch",
                "campaign_message": "Step into Spring with Comfort and Style",
                "target_audience": "Active lifestyle enthusiasts aged 18-35 who value both performance and style",
                "brand_colors": ["#FF6B35", "#004E89", "#FFFFFF"],
                "target_regions": ["US", "CA", "UK"],
                "products": [
                    {
                        "name": "Nike Air Max 270",
                        "description": "Premium running shoe with visible Air unit, breathable mesh upper in modern athletic design"
                    },
                    {
                        "name": "Nike Air Max 90",
                        "description": "Classic design with visible Max Air cushioning and timeless colorways"
                    }
                ]
            },
            "Tech Product Launch": {
                "campaign_name": "Apple Fall Collection",
                "campaign_message": "Innovation at Your Fingertips",
                "target_audience": "Tech enthusiasts and professionals who value cutting-edge technology",
                "brand_colors": ["#000000", "#FFFFFF"],
                "target_regions": ["US", "EU", "JP"],
                "products": [
                    {
                        "name": "iPhone 15 Pro",
                        "description": "Titanium design smartphone with A17 Pro chip and 48MP camera system"
                    },
                    {
                        "name": "AirPods Pro 2",
                        "description": "Active noise cancellation wireless earbuds with USB-C charging"
                    }
                ]
            }
        }
        
        for name, brief in examples.items():
            with st.expander(f"📋 {name}"):
                st.json(brief)
                if st.button(f"Use This Template", key=name):
                    st.session_state['template'] = brief
                    st.success("✅ Template loaded! Go to the Campaign Builder tab to customize it.")

# ==================== PAGE: TRACK PROGRESS ====================
elif page == "📊 Track Progress":
    st.header("Campaign Progress")
    st.write("Monitor your campaigns as they're being processed.")
    
    # Function selector
    col1, col2 = st.columns([2, 1])
    
    with col1:
        process_names = {
            f"{ENVIRONMENT}-{PROJECT_NAME}-parser": "📋 Campaign Validation",
            f"{ENVIRONMENT}-{PROJECT_NAME}-generator": "🎨 Image Generation", 
            f"{ENVIRONMENT}-{PROJECT_NAME}-variants": "📐 Format Creation"
        }
        
        function = st.selectbox(
            "View Progress for:",
            list(process_names.keys()),
            format_func=lambda x: process_names[x]
        )
    
    with col2:
        time_range = st.selectbox("Show activity from:", ["5 minutes", "15 minutes", "1 hour", "24 hours"])
    
    # Convert time range to minutes
    time_map = {"5 minutes": 5, "15 minutes": 15, "1 hour": 60, "24 hours": 1440}
    since_minutes = time_map[time_range]
    
    if st.button("🔄 Refresh"):
        st.rerun()
    
    st.divider()
    
    # Fetch logs
    try:
        log_group = f"/aws/lambda/{function}"
        
        # Get log streams
        streams_response = clients['logs'].describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if streams_response['logStreams']:
            # Get latest stream
            latest_stream = streams_response['logStreams'][0]['logStreamName']
            
            # Get log events
            start_time = int((datetime.now() - timedelta(minutes=since_minutes)).timestamp() * 1000)
            
            logs_response = clients['logs'].get_log_events(
                logGroupName=log_group,
                logStreamName=latest_stream,
                startTime=start_time,
                startFromHead=False
            )
            
            events = logs_response['events']
            
            if events:
                st.success(f"📊 Showing recent activity ({len(events)} entries from last {time_range})")
                
                # Display logs with business-friendly messages
                for event in reversed(events[-50:]):  # Show last 50 events
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%H:%M:%S')
                    message = event['message'].strip()
                    
                    # Translate technical messages to business-friendly ones
                    if 'ERROR' in message or 'Error' in message:
                        if 'timeout' in message.lower():
                            st.error(f"[{timestamp}] ⚠️ Process is taking longer than expected")
                        elif 'permission' in message.lower():
                            st.error(f"[{timestamp}] ⚠️ Access issue detected")
                        else:
                            st.error(f"[{timestamp}] ❌ An error occurred during processing")
                    elif 'WARNING' in message or 'Warning' in message:
                        st.warning(f"[{timestamp}] ⚠️ Minor issue detected - continuing")
                    elif 'START RequestId' in message:
                        st.info(f"[{timestamp}] 🚀 Campaign processing started")
                    elif 'END RequestId' in message:
                        st.success(f"[{timestamp}] ✅ Step completed successfully")
                    elif 'Generated image' in message:
                        st.success(f"[{timestamp}] 🎨 Product image created")
                    elif 'variants' in message.lower():
                        st.success(f"[{timestamp}] 📐 Social media formats created")
                    else:
                        # Hide very technical messages, show simplified version
                        if not any(tech in message.lower() for tech in ['lambda', 'requestid', 'duration', 'billed']):
                            st.text(f"[{timestamp}] 📋 {message}")
            else:
                st.info(f"No activity found in the last {time_range}. Your campaigns may be processing quietly.")
        else:
            st.info("No activity detected yet. Create a campaign to see progress here.")
    
    except clients['logs'].exceptions.ResourceNotFoundException:
        st.warning("🔍 No activity logs found. This process hasn't run recently.")
    except Exception as e:
        st.error("Unable to load activity information right now. Please try again later.")
    
    st.divider()
    
    # Queue status
    st.subheader("📬 Campaign Queue")
    
    try:
        # Get queue URL (you'll need to configure this)
        queue_name = f"{ENVIRONMENT}-{PROJECT_NAME}-queue"
        
        # List queues to find URL
        queues = clients['sqs'].list_queues(QueueNamePrefix=queue_name)
        
        if 'QueueUrls' in queues and queues['QueueUrls']:
            queue_url = queues['QueueUrls'][0]
            
            # Get queue attributes
            attrs = clients['sqs'].get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
            )
            
            col1, col2 = st.columns(2)
            with col1:
                waiting = int(attrs['Attributes']['ApproximateNumberOfMessages'])
                st.metric("Campaigns Waiting", waiting)
            with col2:
                processing = int(attrs['Attributes']['ApproximateNumberOfMessagesNotVisible'])
                st.metric("Currently Processing", processing)
                
            if waiting == 0 and processing == 0:
                st.success("✅ All campaigns are up to date!")
            elif waiting > 0:
                st.info(f"⏳ {waiting} campaign(s) waiting to be processed")
        else:
            st.warning("Campaign queue is not available")
    
    except Exception as e:
        st.error("Unable to check campaign queue status right now.")

# ==================== PAGE: VIEW RESULTS ====================
elif page == "🖼️ View Results":
    st.header("Your Campaign Results")
    st.write("Browse and download your completed campaigns.")
    
    try:
        # List all campaigns
        response = clients['s3'].list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix='output/',
            Delimiter='/'
        )
        
        campaigns = []
        for prefix in response.get('CommonPrefixes', []):
            campaign_id = prefix['Prefix'].split('/')[-2]
            campaigns.append(campaign_id)
        
        if campaigns:
            selected_campaign = st.selectbox("Choose a campaign to view:", campaigns)
            
            if selected_campaign:
                # Load manifest
                try:
                    manifest_obj = clients['s3'].get_object(
                        Bucket=BUCKET_NAME,
                        Key=f"output/{selected_campaign}/manifest.json"
                    )
                    manifest = json.loads(manifest_obj['Body'].read())
                    
                    # Display campaign info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Campaign", manifest['campaign_name'])
                    with col2:
                        status_display = "✅ Ready" if manifest['status'] == 'completed' else "⏳ Processing"
                        st.metric("Status", status_display)
                    with col3:
                        st.metric("Investment", f"${manifest.get('total_cost', 0.0):.2f}")
                    
                    st.info(f"💬 **Campaign Message:** {manifest.get('campaign_message', 'N/A')}")
                    
                    st.divider()
                    
                    # Display products (only those with variants)
                    completed_products = [p for p in manifest.get('products', []) if 'variants' in p and p.get('variants')]
                    
                    if not completed_products:
                        st.info("⏳ Your campaign is being processed. Images will appear here once generation is complete.")
                    
                    for product in completed_products:
                        st.subheader(f"📦 {product.get('product_name', product.get('name', 'Unknown Product'))}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Cost", f"${product.get('processing_cost', product.get('cost', 0.0)):.2f}")
                        with col2:
                            formats_count = len(product.get('variants', []))
                            st.metric("Social Formats", f"{formats_count} created")
                        
                        # Display generated image
                        image_key = product.get('image_key', '')
                        if image_key:
                            try:
                                img_obj = clients['s3'].get_object(Bucket=BUCKET_NAME, Key=image_key)
                                img = Image.open(BytesIO(img_obj['Body'].read()))
                                
                                st.image(img, caption="Original Product Image (High Resolution)", use_container_width=True)
                                
                                # Download button
                                img_bytes = BytesIO()
                                img.save(img_bytes, format='PNG')
                                st.download_button(
                                    "📥 Download Original Image",
                                    data=img_bytes.getvalue(),
                                    file_name=f"{product['name']}-original.png",
                                    mime="image/png"
                                )
                            except Exception as e:
                                st.error("Unable to load the product image right now.")
                        
                        # Display variants
                        st.subheader("📱 Social Media Ready Formats")
                        
                        platform_names = {
                            "instagram-square": "📱 Instagram Post",
                            "instagram-story": "📱 Instagram Story", 
                            "facebook-feed": "👥 Facebook Post",
                            "twitter-card": "🐦 Twitter Card",
                            "linkedin-post": "💼 LinkedIn Post"
                        }
                        
                        # Get variants from product
                        variants_list = product.get('variants', [])
                        
                        if variants_list:
                            cols = st.columns(min(5, len(variants_list)))
                            
                            for idx, variant_info in enumerate(variants_list):
                                variant_key = variant_info.get('key', '')
                                variant_platform = variant_info.get('platform', '')
                                
                                if variant_key:
                                    try:
                                        variant_obj = clients['s3'].get_object(Bucket=BUCKET_NAME, Key=variant_key)
                                        variant_img = Image.open(BytesIO(variant_obj['Body'].read()))
                                        
                                        with cols[idx]:
                                            st.image(variant_img, caption=platform_names.get(variant_platform, variant_platform), use_container_width=True)
                                            
                                            # Download button
                                            var_bytes = BytesIO()
                                            variant_img.save(var_bytes, format='JPEG')
                                            product_idx = product.get('product_index', product.get('index', idx))
                                            st.download_button(
                                                "📥",
                                                data=var_bytes.getvalue(),
                                                file_name=f"{product.get('product_name', 'product')}-{variant_platform}.jpg",
                                                mime="image/jpeg",
                                                key=f"dl_{product_idx}_{variant_platform}"
                                            )
                                    except Exception as e:
                                        with cols[idx]:
                                            st.warning("Not ready yet")
                        else:
                            st.info("⏳ Social media formats are being created...")
                        
                        st.divider()
                    
                    # Download all button
                    if st.button("📦 Download Complete Campaign"):
                        st.info(f"💡 **Pro Tip:** To download all files at once, use this command in your terminal:\n\n`aws s3 sync s3://{BUCKET_NAME}/output/{selected_campaign}/ ./my-campaign/`")
                
                except Exception as e:
                    st.error("We're having trouble loading this campaign. Please try refreshing or contact support.")
        else:
            st.info("🚀 No campaigns completed yet. Create your first campaign to see results here!")
    
    except Exception as e:
        st.error("Unable to load campaigns at the moment. Please try again later.")

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    Built with ❤️ using Streamlit | Powered by Amazon Bedrock Titan Image Generator
</div>
""", unsafe_allow_html=True)
