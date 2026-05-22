"""Upload complete endpoint — POST /api/upload/complete."""

import azure.functions as func
from pydantic import ValidationError

from models.complete import UploadCompleteRequest
from services.auth import AuthenticationError, authenticate_request
from services.blob_storage import BlobStorageError
from services.cosmos_db import CosmosDbError, TripLogNotFoundError
from services.event_hub import EventHubError
from services.upload_complete_service import UploadCompleteService
from shared.correlation import bind_correlation_id
from shared.http import json_response
from shared.logging import get_logger

bp = func.Blueprint()
logger = get_logger(__name__)


@bp.route(route="upload/complete", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def upload_complete(req: func.HttpRequest) -> func.HttpResponse:
    """Validate blobs, update Cosmos, publish Event Hub event."""
    correlation_id = bind_correlation_id(req.headers.get("x-correlation-id"))

    try:
        authenticate_request(req.headers.get("Authorization"))
        body = UploadCompleteRequest.model_validate_json(req.get_body())
    except AuthenticationError as exc:
        logger.info(
            {
                "operation": "upload_complete",
                "status": "FAILED",
                "correlation_id": correlation_id,
                "error": str(exc),
            },
        )
        return json_response({"error": "unauthorized", "message": str(exc)}, status_code=401)
    except ValidationError as exc:
        return json_response(
            {"error": "validation_error", "details": exc.errors()},
            status_code=400,
        )

    try:
        response = UploadCompleteService().complete_upload(
            request=body,
            correlation_id=correlation_id,
        )
    except TripLogNotFoundError:
        return json_response(
            {"error": "not_found", "message": "upload session not found"},
            status_code=404,
        )
    except (BlobStorageError, CosmosDbError, EventHubError) as exc:
        logger.info(
            {
                "operation": "upload_complete",
                "status": "FAILED",
                "correlation_id": correlation_id,
                "route_id": body.route_id,
                "upload_session_id": body.upload_session_id,
                "error": str(exc),
            },
        )
        return json_response(
            {"error": "service_unavailable", "message": str(exc)},
            status_code=503,
        )

    logger.info(
        {
            "operation": "upload_complete",
            "status": "SUCCESS",
            "correlation_id": correlation_id,
            "route_id": body.route_id,
            "upload_session_id": body.upload_session_id,
            "validation_status": response.validation_status.value,
        },
    )
    return json_response(response, status_code=200)
