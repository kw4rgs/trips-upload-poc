"""Upload session endpoint — POST /api/upload/session."""

import azure.functions as func
from pydantic import ValidationError

from models.session import UploadSessionRequest
from services.auth import (
    AuthenticationError,
    authenticate_request,
)
from services.blob_storage import BlobStorageError
from services.cosmos_db import CosmosDbError
from services.upload_session_service import UploadSessionService
from shared.correlation import bind_correlation_id
from shared.http import json_response
from shared.logging import get_logger

bp = func.Blueprint()
logger = get_logger(__name__)


@bp.route(route="upload/session", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def upload_session(req: func.HttpRequest) -> func.HttpResponse:
    """Create upload session, SAS URLs, and trip log entry."""
    correlation_id = bind_correlation_id(req.headers.get("x-correlation-id"))

    try:
        user_id = authenticate_request(req.headers.get("Authorization"))
        body = UploadSessionRequest.model_validate_json(req.get_body())
    except AuthenticationError as exc:
        logger.info(
            {
                "operation": "upload_session",
                "status": "FAILED",
                "correlation_id": correlation_id,
                "error": str(exc),
            },
        )
        return json_response({"error": "unauthorized", "message": str(exc)}, status_code=401)
    except ValidationError as exc:
        logger.info(
            {
                "operation": "upload_session",
                "status": "FAILED",
                "correlation_id": correlation_id,
                "error": "validation_error",
            },
        )
        return json_response(
            {"error": "validation_error", "details": exc.errors()},
            status_code=400,
        )

    try:
        response = UploadSessionService().create_session(
            route_id=body.route_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )
    except (BlobStorageError, CosmosDbError) as exc:
        logger.info(
            {
                "operation": "upload_session",
                "status": "FAILED",
                "correlation_id": correlation_id,
                "route_id": body.route_id,
                "error": str(exc),
            },
        )
        return json_response(
            {"error": "service_unavailable", "message": str(exc)},
            status_code=503,
        )

    logger.info(
        {
            "operation": "upload_session",
            "status": "SUCCESS",
            "correlation_id": correlation_id,
            "route_id": body.route_id,
            "upload_session_id": response.upload_session_id,
        },
    )
    return json_response(response, status_code=201)
