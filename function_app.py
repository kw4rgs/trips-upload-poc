"""Azure Functions entrypoint — registers API v1 blueprints."""

from shared.telemetry import configure_telemetry

configure_telemetry()

import azure.functions as func

from api.v1.health import health_bp
from api.v1.upload_complete import bp as upload_complete_bp
from api.v1.upload_session import bp as upload_session_bp

app = func.FunctionApp()

app.register_functions(health_bp)
app.register_functions(upload_session_bp)
app.register_functions(upload_complete_bp)
