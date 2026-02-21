#!/bin/bash

# NeuralBlitz AWS Lambda Deployment Script
# Usage: ./deploy.sh [environment] [region]

set -e

ENVIRONMENT=${1:-production}
REGION=${2:-us-east-1}
STACK_NAME="neuralblitz-${ENVIRONMENT}"
DEPLOYMENT_BUCKET="neuralblitz-deployments-${REGION}-${AWS_ACCOUNT_ID:-123456789012}"

echo "========================================="
echo "NeuralBlitz AWS Lambda Deployment"
echo "========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo "Stack Name: ${STACK_NAME}"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
command -v aws >/dev/null 2>&1 || { echo "AWS CLI is required but not installed. Aborting." >&2; exit 1; }
command -v sam >/dev/null 2>&1 || { echo "AWS SAM CLI is required but not installed. Aborting." >&2; exit 1; }

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: ${AWS_ACCOUNT_ID}"

# Create deployment bucket if it doesn't exist
echo "Creating deployment bucket..."
if ! aws s3api head-bucket --bucket "${DEPLOYMENT_BUCKET}" 2>/dev/null; then
    aws s3 mb "s3://${DEPLOYMENT_BUCKET}" --region ${REGION}
    echo "Created bucket: ${DEPLOYMENT_BUCKET}"
else
    echo "Bucket ${DEPLOYMENT_BUCKET} already exists"
fi

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt -t src/

# Run tests
echo "Running tests..."
if [ -d "tests" ]; then
    python -m pytest tests/ -v || { echo "Tests failed!"; exit 1; }
fi

# Package the application
echo "Packaging application..."
sam package \
    --template-file template.yaml \
    --output-template-file packaged.yaml \
    --s3-bucket "${DEPLOYMENT_BUCKET}" \
    --region ${REGION}

# Deploy the stack
echo "Deploying stack..."
sam deploy \
    --template-file packaged.yaml \
    --stack-name "${STACK_NAME}" \
    --s3-bucket "${DEPLOYMENT_BUCKET}" \
    --region ${REGION} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
    --parameter-overrides \
        Environment="${ENVIRONMENT}" \
    --no-fail-on-empty-changeset

# Get stack outputs
echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo "To test the deployment:"
echo "curl -X POST $(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' --output text)inference -H 'Content-Type: application/json' -d '{\"input_data\": {\"test\": true}}'"
