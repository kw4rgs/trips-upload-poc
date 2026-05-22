"""Health check endpoint."""

import azure.functions as func

from shared.correlation import bind_correlation_id, get_correlation_id
from shared.http import json_response
from shared.logging import get_logger

health_bp = func.Blueprint()
logger = get_logger(__name__)


@health_bp.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Liveness probe for load balancers and deployment verification."""
    bind_correlation_id(req.headers.get("x-correlation-id"))
    logger.info({"operation": "health", "status": "SUCCESS"})
    return json_response(
        {
            "status": "ok",
            "service": "trips-upload-poc",
            "correlation_id": get_correlation_id(),
        },
        status_code=200,
    )
