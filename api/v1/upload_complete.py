"""Upload complete endpoint — POST /api/upload/complete."""

import azure.functions as func
from pydantic import ValidationError

from models.complete import UploadCompleteRequest, ValidationStatus
from services.auth import AuthenticationError, authenticate_request
from services.blob_storage import BlobStorageError
from services.cosmos_db import CosmosConflictError, CosmosDbError, TripLogNotFoundError
from services.event_hub import EventHubError
from services.upload_complete_service import TripOwnershipError, UploadCompleteService
from shared.correlation import bind_correlation_id
from shared.errors import ErrorCode, error_response
from shared.http import json_response
from shared.logging import get_logger
from shared.telemetry import set_operation_attributes

bp = func.Blueprint()
logger = get_logger(__name__)


@bp.route(route="upload/complete", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def upload_complete(req: func.HttpRequest) -> func.HttpResponse:
    """Validate blobs, update Cosmos, publish Event Hub event."""
    correlation_id = bind_correlation_id(req.headers.get("x-correlation-id"))
    set_operation_attributes(correlation_id=correlation_id, operation="upload_complete")

    try:
        user_id = authenticate_request(req.headers.get("Authorization"))
        body = UploadCompleteRequest.model_validate_json(req.get_body())
    except AuthenticationError as exc:
        logger.info(
            {
                "operation": "upload_complete",
                "status": "FAILED",
                "correlation_id": correlation_id,
                "error": ErrorCode.UNAUTHORIZED.value,
            },
        )
        return error_response(
            error=ErrorCode.UNAUTHORIZED,
            message=str(exc),
            status_code=401,
            correlation_id=correlation_id,
        )
    except ValidationError as exc:
        logger.warning(
            {
                "operation": "upload_complete",
                "status": "FAILED",
                "correlation_id": correlation_id,
                "error": ErrorCode.VALIDATION_ERROR.value,
            },
        )
        return error_response(
            error=ErrorCode.VALIDATION_ERROR,
            message="request validation failed",
            status_code=400,
            correlation_id=correlation_id,
            details=exc.errors(),
        )

    set_operation_attributes(
        route_id=body.route_id,
        upload_session_id=body.upload_session_id,
    )

    try:
        response = UploadCompleteService().complete_upload(
            request=body,
            correlation_id=correlation_id,
            caller_user_id=user_id,
        )
    except TripOwnershipError:
        logger.warning(
            {
                "operation": "upload_complete",
                "status": "FORBIDDEN",
                "correlation_id": correlation_id,
                "upload_session_id": body.upload_session_id,
            },
        )
        return error_response(
            error=ErrorCode.UNAUTHORIZED,
            message="you do not own this upload session",
            status_code=403,
            correlation_id=correlation_id,
        )
    except TripLogNotFoundError:
        return error_response(
            error=ErrorCode.NOT_FOUND,
            message="upload session not found",
            status_code=404,
            correlation_id=correlation_id,
        )
    except CosmosConflictError:
        logger.warning(
            {
                "operation": "upload_complete",
                "status": "CONFLICT",
                "correlation_id": correlation_id,
                "upload_session_id": body.upload_session_id,
            },
        )
        return error_response(
            error=ErrorCode.CONFLICT,
            message="concurrent complete request detected — retry after a moment",
            status_code=409,
            correlation_id=correlation_id,
        )
    except (BlobStorageError, CosmosDbError, EventHubError):
        logger.error(
            {
                "operation": "upload_complete",
                "status": "FAILED",
                "correlation_id": correlation_id,
                "route_id": body.route_id,
                "upload_session_id": body.upload_session_id,
                "error": ErrorCode.SERVICE_UNAVAILABLE.value,
            },
            exc_info=True,
        )
        return error_response(
            error=ErrorCode.SERVICE_UNAVAILABLE,
            message="an upstream service is temporarily unavailable",
            status_code=503,
            correlation_id=correlation_id,
        )

    status_code = 200
    if response.validation_status == ValidationStatus.FAILED:
        status_code = 409

    logger.info(
        {
            "operation": "upload_complete",
            "status": "SUCCESS" if status_code == 200 else "VALIDATION_FAILED",
            "correlation_id": correlation_id,
            "route_id": body.route_id,
            "upload_session_id": body.upload_session_id,
            "validation_status": response.validation_status.value,
        },
    )
    return json_response(response, status_code=status_code)
