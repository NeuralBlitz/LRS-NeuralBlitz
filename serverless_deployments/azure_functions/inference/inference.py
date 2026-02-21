"""
Azure Functions HTTP Trigger for NeuralBlitz Inference
"""

import logging
import json
import os
import uuid
from datetime import datetime
from azure.functions import HttpRequest, HttpResponse, Out
import azure.functions as func

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main(req: HttpRequest, outputDocument: Out[func.Document]) -> HttpResponse:
    """
    Main entry point for Azure Function
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Processing inference request: {request_id}")

    try:
        # Parse request body
        req_body = req.get_json()

        # Validate required fields
        if "input_data" not in req_body:
            return HttpResponse(
                body=json.dumps(
                    {
                        "success": False,
                        "error": {
                            "message": "Missing required field: input_data",
                            "code": "MISSING_FIELD",
                        },
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ),
                status_code=400,
                mimetype="application/json",
            )

        # Process inference
        result = process_inference(
            input_data=req_body["input_data"],
            model_config=req_body.get("model_config", {}),
            request_id=request_id,
        )

        # Store in Cosmos DB
        outputDocument.set(
            func.Document.from_dict(
                {
                    "id": request_id,
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": req_body.get("user_id", "anonymous"),
                    "input_data": req_body["input_data"],
                    "result": result,
                    "ttl": 2592000,  # 30 days
                }
            )
        )

        # Return success response
        return HttpResponse(
            body=json.dumps(
                {
                    "success": True,
                    "data": result,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            status_code=200,
            mimetype="application/json",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logger.error(f"Invalid JSON in request: {str(e)}")
        return HttpResponse(
            body=json.dumps(
                {
                    "success": False,
                    "error": {
                        "message": "Invalid JSON in request body",
                        "code": "INVALID_JSON",
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            status_code=400,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Error processing request {request_id}: {str(e)}", exc_info=True)
        return HttpResponse(
            body=json.dumps(
                {
                    "success": False,
                    "error": {
                        "message": "Internal processing error",
                        "code": "INTERNAL_ERROR",
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            status_code=500,
            mimetype="application/json",
        )


def process_inference(input_data, model_config, request_id):
    """
    Core inference logic
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
            "provider": "Azure",
        },
    }

    return result
