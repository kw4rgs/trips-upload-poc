"""Health check endpoint."""

import azure.functions as func

health_bp = func.Blueprint()


@health_bp.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Liveness probe for local dev and deployment verification."""
    return func.HttpResponse(
        body='{"status":"ok","service":"trips-upload-poc"}',
        mimetype="application/json",
        status_code=200,
    )
