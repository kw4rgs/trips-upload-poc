"""Health check endpoint."""

import azure.functions as func

from shared.correlation import bind_correlation_id
from shared.logging import get_logger

health_bp = func.Blueprint()
logger = get_logger(__name__)


@health_bp.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Liveness probe for local dev and deployment verification."""
    correlation_id = bind_correlation_id(
        req.headers.get("x-correlation-id"),
    )
    logger.info(
        {
            "operation": "health",
            "status": "SUCCESS",
        },
    )
    return func.HttpResponse(
        body=f'{{"status":"ok","service":"trips-upload-poc","correlation_id":"{correlation_id}"}}',
        mimetype="application/json",
        status_code=200,
    )
