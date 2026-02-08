from __future__ import annotations

from flask import Blueprint, Response, current_app, request

slack_bp = Blueprint("slack", __name__)


@slack_bp.post("/slack/events")
def slack_events() -> Response:
    handler = current_app.extensions.get("slack_handler")
    error = current_app.extensions.get("slack_error")

    if handler is None:
        return Response(f"Slack is not configured: {error}\n", status=500)

    return handler.handle(request)  # type: ignore[no-any-return]

