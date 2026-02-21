#!/bin/bash

# NeuralBlitz Azure Functions Deployment Script
# Usage: ./deploy.sh [environment] [resource-group]

set -e

ENVIRONMENT=${1:-production}
RESOURCE_GROUP=${2:-neuralblitz-rg}
LOCATION=${3:-eastus}
FUNCTION_APP_NAME="neuralblitz-functions-${ENVIRONMENT}"

echo "========================================="
echo "NeuralBlitz Azure Functions Deployment"
echo "========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Location: ${LOCATION}"
echo "Function App: ${FUNCTION_APP_NAME}"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
command -v az >/dev/null 2>&1 || { echo "Azure CLI is required but not installed. Aborting." >&2; exit 1; }
command -v func >/dev/null 2>&1 || { echo "Azure Functions Core Tools is required but not installed. Aborting." >&2; exit 1; }

# Login to Azure (if not already logged in)
echo "Checking Azure login status..."
az account show >/dev/null 2>&1 || az login

# Create resource group if it doesn't exist
echo "Creating resource group..."
az group create \
    --name "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --tags environment="${ENVIRONMENT}" project="neuralblitz" \
    --output none || echo "Resource group ${RESOURCE_GROUP} already exists"

# Deploy infrastructure
echo "Deploying Azure infrastructure..."
az deployment group create \
    --resource-group "${RESOURCE_GROUP}" \
    --template-file azuredeploy.json \
    --parameters functionAppName="${FUNCTION_APP_NAME}" environment="${ENVIRONMENT}" \
    --output none

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt --target .python_packages/lib/site-packages

# Publish function app
echo "Publishing Function App..."
func azure functionapp publish "${FUNCTION_APP_NAME}"

# Get function app URL
FUNCTION_URL=$(az functionapp show \
    --name "${FUNCTION_APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query defaultHostName \
    --output tsv)

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo "Function App URL: https://${FUNCTION_URL}"
echo ""
echo "To test the deployment:"
echo "curl -X POST https://${FUNCTION_URL}/api/inference -H 'Content-Type: application/json' -d '{\"input_data\": {\"test\": true}}'"

# Get Application Insights key
echo ""
echo "Monitoring:"
az monitor app-insights component show \
    --app "${FUNCTION_APP_NAME}-insights" \
    --resource-group "${RESOURCE_GROUP}" \
    --query '{InstrumentationKey:instrumentationKey, ConnectionString:connectionString}' \
    --output table || echo "App Insights not found"
