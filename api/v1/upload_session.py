"""Upload session endpoint — POST /api/upload/session."""

import azure.functions as func

bp = func.Blueprint()


@bp.route(route="upload/session", methods=["POST"])
def upload_session(req: func.HttpRequest) -> func.HttpResponse:
    """Create upload session, SAS URLs, and trip log entry (T08)."""
    return func.HttpResponse(
        body='{"error":"not_implemented","endpoint":"upload/session"}',
        mimetype="application/json",
        status_code=501,
    )
