# NeuralBlitz Serverless Deployments

## Overview

This directory contains three complete serverless deployment configurations for the NeuralBlitz platform:

1. **AWS Lambda** - Event-driven serverless compute
2. **Azure Functions** - Microsoft's serverless offering
3. **Google Cloud Run** - Container-based serverless platform

## Quick Start

### AWS Lambda
```bash
cd aws_lambda
./deploy.sh production us-east-1
```

### Azure Functions
```bash
cd azure_functions
./deploy.sh production neuralblitz-rg eastus
```

### Google Cloud Run
```bash
cd google_cloud_run
./deploy.sh neuralblitz-project us-central1
```

## Directory Structure

```
serverless_deployments/
├── SERVERLESS_DEPLOYMENT_REPORT.md    # Detailed comparison report
├── aws_lambda/                        # AWS Lambda configuration
│   ├── template.yaml                  # SAM/CloudFormation template
│   ├── deploy.sh                      # Deployment script
│   ├── requirements.txt               # Python dependencies
│   └── src/handlers/
│       └── inference.py               # Lambda handlers
├── azure_functions/                   # Azure Functions configuration
│   ├── host.json                      # Function app configuration
│   ├── azuredeploy.json               # ARM template
│   ├── deploy.sh                      # Deployment script
│   ├── requirements.txt               # Python dependencies
│   └── inference/
│       ├── function.json              # Function bindings
│       └── inference.py               # Function code
└── google_cloud_run/                  # Cloud Run configuration
    ├── Dockerfile                     # Container definition
    ├── main.py                        # Flask application
    ├── service.yaml                   # Cloud Run service spec
    ├── main.tf                        # Terraform infrastructure
    ├── deploy.sh                      # Deployment script
    └── requirements.txt               # Python dependencies
```

## Features

All three deployment options include:

- **Inference API**: RESTful endpoint for processing requests
- **Governance Check**: Ethics and compliance validation
- **Audit Logging**: Comprehensive audit trail
- **Auto-scaling**: Automatic scaling based on load
- **Monitoring**: Integrated logging and tracing
- **Security**: IAM/RBAC, encryption, and VPC support

## Requirements

### Common
- Docker
- Python 3.11+
- Git

### AWS
- AWS CLI
- SAM CLI

### Azure
- Azure CLI
- Azure Functions Core Tools

### Google Cloud
- Google Cloud SDK (gcloud)
- Terraform (optional)

## Configuration

Each platform has environment-specific configuration:

- **AWS**: Use `template.yaml` parameters
- **Azure**: Use `local.settings.json` for local, ARM template for production
- **GCP**: Use Terraform variables or gcloud CLI flags

## Testing

All deployments include health check endpoints:

```bash
# AWS
curl https://API_ID.execute-api.REGION.amazonaws.com/production/health

# Azure
curl https://FUNCTION_APP.azurewebsites.net/api/health

# GCP
curl https://SERVICE_URL/health
```

## Documentation

See `SERVERLESS_DEPLOYMENT_REPORT.md` for detailed comparison, cost analysis, and recommendations.

## License

MIT License - See LICENSE file for details
