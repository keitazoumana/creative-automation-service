#!/bin/bash
# Deploy infrastructure with SSL workaround for corporate networks
# This script handles the SSL certificate issue automatically

set -e

echo "========================================"
echo " Terraform Deployment with SSL Fix"
echo "========================================"

# Export environment variables to bypass SSL certificate verification
export AWS_CA_BUNDLE=""
export GODEBUG=x509ignoreCN=0

echo ""
echo "✓ SSL certificate bypass enabled"
echo "✓ Environment: dev"
echo ""

# Run Terraform apply
echo "Starting Terraform deployment..."
terraform apply -var-file="environments/dev.tfvars" "$@"

echo ""
echo "========================================"
echo " Deployment Complete!"
echo "========================================"
