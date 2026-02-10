from __future__ import annotations

from flask import Blueprint, Response, current_app, request

slack_bp = Blueprint("slack", __name__)


@slack_bp.post("/")
@slack_bp.post("/slack/events")
def slack_events() -> Response:
    handler = current_app.extensions.get("slack_handler")
    error = current_app.extensions.get("slack_error")

    if handler is None:
        # Slack から見ると 500/タイムアウトは `dispatch_failed` になりやすく、
        # ユーザーに原因が伝わらないため、Slash Command だけは 200 で明示メッセージを返す。
        try:
            is_slash_command = request.form.get("command") is not None
        except Exception:
            is_slash_command = False

        msg = f"Slack が未設定です: {error}\n" if error else "Slack が未設定です。\n"
        if is_slash_command:
            return Response(msg, status=200, content_type="text/plain; charset=utf-8")
        return Response(msg, status=500, content_type="text/plain; charset=utf-8")

    return handler.handle(request)  # type: ignore[no-any-return]

