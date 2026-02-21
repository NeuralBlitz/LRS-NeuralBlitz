"""
Azure Functions Cosmos DB Trigger for Audit Logging
"""

import logging
import json
from datetime import datetime
import azure.functions as func

logger = logging.getLogger(__name__)


def main(documents: func.DocumentList, auditBlob: func.Out[str]) -> None:
    """
    Process Cosmos DB changes and write to audit blob storage
    """
    audit_logs = []

    for doc in documents:
        try:
            audit_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "DOCUMENT_INSERT" if doc.get("id") else "DOCUMENT_UPDATE",
                "request_id": doc.get("request_id", "unknown"),
                "user_id": doc.get("user_id", "unknown"),
                "collection": "results",
                "document_id": doc.get("id", "unknown"),
            }

            audit_logs.append(audit_log)
            logger.info(f"Audit log entry: {audit_log['request_id']}")

        except Exception as e:
            logger.error(f"Error processing document for audit: {str(e)}")

    # Write all audit logs to blob
    if audit_logs:
        auditBlob.set(json.dumps(audit_logs, indent=2))
        logger.info(f"Written {len(audit_logs)} audit log entries")
