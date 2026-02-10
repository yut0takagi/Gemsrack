from __future__ import annotations

import traceback

from flask import Blueprint, Response, current_app, request

slack_bp = Blueprint("slack", __name__)


@slack_bp.post("/")
@slack_bp.post("/slack/events")
def slack_events() -> Response:
    handler = current_app.extensions.get("slack_handler")
    error = current_app.extensions.get("slack_error")

    # Slash Command かどうか（失敗時に 200 で理由を返すため）
    try:
        is_slash_command = request.form.get("command") is not None
    except Exception:
        is_slash_command = False

    if handler is None:
        # Slack から見ると 500/タイムアウトは `dispatch_failed` になりやすく、
        # ユーザーに原因が伝わらないため、Slash Command だけは 200 で明示メッセージを返す。
        msg = f"Slack が未設定です: {error}\n" if error else "Slack が未設定です。\n"
        if is_slash_command:
            return Response(msg, status=200, content_type="text/plain; charset=utf-8")
        return Response(msg, status=500, content_type="text/plain; charset=utf-8")

    try:
        return handler.handle(request)  # type: ignore[no-any-return]
    except Exception as e:
        # Slack からは `dispatch_failed` に見えることが多いので、ログにスタックトレースを残す
        print(
            "[slack] handler failed:",
            type(e).__name__,
            str(e),
            "path=",
            request.path,
            "content_type=",
            request.content_type,
        )
        print(traceback.format_exc())
        msg = f"Slack リクエスト処理で例外が発生しました: `{type(e).__name__}`\n"
        if is_slash_command:
            return Response(msg, status=200, content_type="text/plain; charset=utf-8")
        return Response(msg, status=500, content_type="text/plain; charset=utf-8")

