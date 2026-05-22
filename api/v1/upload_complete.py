"""Upload complete endpoint — POST /api/upload/complete."""

import azure.functions as func

bp = func.Blueprint()


@bp.route(route="upload/complete", methods=["POST"])
def upload_complete(req: func.HttpRequest) -> func.HttpResponse:
    """Validate blobs, update Cosmos, publish Event Hub event (T09)."""
    return func.HttpResponse(
        body='{"error":"not_implemented","endpoint":"upload/complete"}',
        mimetype="application/json",
        status_code=501,
    )
