"""Azure Functions entrypoint for trips-upload-poc Upload Service."""

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Liveness probe for local dev and deployment verification."""
    return func.HttpResponse(
        body='{"status":"ok","service":"trips-upload-poc"}',
        mimetype="application/json",
        status_code=200,
    )
