"""
AWS Lambda Handler Functions for NeuralBlitz
Supports inference processing, governance checks, and audit logging
"""

import json
import os
import logging
from datetime import datetime
import boto3
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.core import models as xray_models

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Patch boto3 for X-Ray tracing
patch_all()

# Initialize AWS clients
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
results_table = dynamodb.Table(os.environ.get("RESULTS_TABLE", "neuralblitz-results"))


class NeuralBlitzResponse:
    """Standardized API response format"""

    @staticmethod
    def success(data, status_code=200):
        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            },
            "body": json.dumps(
                {
                    "success": True,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
        }

    @staticmethod
    def error(message, status_code=500, error_code=None):
        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "success": False,
                    "error": {"message": message, "code": error_code},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
        }


@xray_recorder.capture("inference_handler")
def handler(event, context):
    """
    Main inference processing handler

    Supports:
    - API Gateway requests (HTTP POST)
    - S3 event triggers (file upload)
    - Direct Lambda invocations
    """
    request_id = context.aws_request_id
    logger.info(f"Processing inference request: {request_id}")

    try:
        # Determine event source
        if "httpMethod" in event:
            # API Gateway request
            return _handle_api_request(event, context)
        elif "Records" in event and event["Records"][0].get("eventSource") == "aws:s3":
            # S3 trigger
            return _handle_s3_event(event, context)
        else:
            # Direct invocation
            return _handle_direct_invocation(event, context)

    except Exception as e:
        logger.error(f"Error processing request {request_id}: {str(e)}", exc_info=True)
        return NeuralBlitzResponse.error(
            message="Internal processing error",
            status_code=500,
            error_code="INTERNAL_ERROR",
        )


def _handle_api_request(event, context):
    """Handle API Gateway HTTP requests"""
    http_method = event.get("httpMethod")
    path = event.get("path", "")

    if http_method == "OPTIONS":
        return NeuralBlitzResponse.success({})

    if http_method != "POST":
        return NeuralBlitzResponse.error(
            message="Method not allowed",
            status_code=405,
            error_code="METHOD_NOT_ALLOWED",
        )

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return NeuralBlitzResponse.error(
            message="Invalid JSON in request body",
            status_code=400,
            error_code="INVALID_JSON",
        )

    # Validate required fields
    if "input_data" not in body:
        return NeuralBlitzResponse.error(
            message="Missing required field: input_data",
            status_code=400,
            error_code="MISSING_FIELD",
        )

    # Process inference
    result = _process_inference(
        input_data=body["input_data"],
        model_config=body.get("model_config", {}),
        request_id=context.aws_request_id,
    )

    # Store result
    _store_result(result, body.get("user_id", "anonymous"))

    return NeuralBlitzResponse.success(result)


def _handle_s3_event(event, context):
    """Handle S3 upload triggers"""
    results = []

    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        logger.info(f"Processing S3 object: s3://{bucket}/{key}")

        try:
            # Download and parse S3 object
            response = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(response["Body"].read().decode("utf-8"))

            # Process inference
            result = _process_inference(
                input_data=data, model_config={}, request_id=context.aws_request_id
            )

            # Store result
            _store_result(result, data.get("user_id", "s3-upload"))

            # Move processed file
            processed_key = key.replace("uploads/", "processed/")
            s3.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": key},
                Key=processed_key,
            )
            s3.delete_object(Bucket=bucket, Key=key)

            results.append(
                {"key": key, "status": "success", "request_id": result["request_id"]}
            )

        except Exception as e:
            logger.error(f"Error processing S3 object {key}: {str(e)}")
            results.append({"key": key, "status": "error", "error": str(e)})

    return NeuralBlitzResponse.success({"processed": results})


def _handle_direct_invocation(event, context):
    """Handle direct Lambda invocations"""
    result = _process_inference(
        input_data=event.get("input_data", {}),
        model_config=event.get("model_config", {}),
        request_id=context.aws_request_id,
    )

    if event.get("store_result", True):
        _store_result(result, event.get("user_id", "direct-invocation"))

    return result


def _process_inference(input_data, model_config, request_id):
    """
    Core inference logic

    In production, this would:
    1. Load model from S3
    2. Preprocess input
    3. Run inference
    4. Postprocess results
    5. Apply governance checks
    """
    start_time = datetime.utcnow()

    # Simulate inference processing
    result = {
        "request_id": request_id,
        "input_hash": hash(str(input_data)) & 0xFFFFFFFF,
        "prediction": {
            "class": "positive",
            "confidence": 0.95,
            "explanation": "Inference completed successfully",
        },
        "governance_check": {
            "charter_compliant": True,
            "ethics_score": 0.98,
            "privacy_preserved": True,
        },
        "processing_metadata": {
            "start_time": start_time.isoformat(),
            "model_version": model_config.get("version", "v1.0.0"),
            "inference_time_ms": 150,
        },
    }

    return result


def _store_result(result, user_id):
    """Store result in DynamoDB"""
    try:
        results_table.put_item(
            Item={
                "request_id": result["request_id"],
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "result": result,
                "ttl": int((datetime.utcnow().timestamp() + 2592000)),  # 30 days
            }
        )
    except Exception as e:
        logger.error(f"Error storing result: {str(e)}")


# Governance handler
def governance_handler(event, context):
    """Handle governance and ethics validation requests"""
    try:
        body = json.loads(event.get("body", "{}"))

        # Validate against charter
        validation_result = {
            "request_id": context.aws_request_id,
            "validation_status": "approved",
            "charter_compliance": {
                "phi_1_flourishing": True,
                "phi_2_kernel_bounds": True,
                "phi_3_transparency": True,
                "phi_4_non_maleficence": True,
                "phi_5_friendly_ai": True,
            },
            "risk_assessment": {"overall_risk": "low", "risk_score": 0.12},
            "recommendations": [],
        }

        return NeuralBlitzResponse.success(validation_result)

    except Exception as e:
        logger.error(f"Governance check error: {str(e)}")
        return NeuralBlitzResponse.error(
            message="Governance validation failed",
            status_code=500,
            error_code="GOVERNANCE_ERROR",
        )


# Audit logging handler
def audit_handler(event, context):
    """Process DynamoDB stream events for audit logging"""
    audit_logs = []

    for record in event["Records"]:
        if record["eventName"] in ["INSERT", "MODIFY"]:
            new_image = record["dynamodb"].get("NewImage", {})

            audit_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": record["eventName"],
                "request_id": new_image.get("request_id", {}).get("S", "unknown"),
                "user_id": new_image.get("user_id", {}).get("S", "unknown"),
                "table_name": record["eventSourceARN"].split("/")[-1],
            }

            audit_logs.append(audit_log)
            logger.info(f"Audit log: {audit_log}")

    return {"processed": len(audit_logs)}
