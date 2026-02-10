from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from .registry import register_all


@dataclass(frozen=True)
class SlackBuildResult:
    app: object | None
    handler: object | None
    error: str | None


def build_slack(settings: Settings) -> SlackBuildResult:
    if not settings.slack_bot_token or not settings.slack_signing_secret:
        return SlackBuildResult(
            app=None,
            handler=None,
            error="SLACK_BOT_TOKEN / SLACK_SIGNING_SECRET が未設定です",
        )

    try:
        from slack_bolt import App
        from slack_bolt.adapter.flask import SlackRequestHandler
    except Exception:
        return SlackBuildResult(
            app=None,
            handler=None,
            error="依存関係が未導入です（pip install -r requirements.txt）",
        )

    try:
        slack_app = App(
            token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret,
            # Slack は 3 秒以内に 200 を期待するため、長処理（AI生成等）はレスポンス後に実行する
            process_before_response=False,
        )
    except Exception as e:
        # invalid_auth 等で Bolt が起動時に例外を投げることがある。
        # Slack が使えなくても /health や Web UI / API は起動できるようにする。
        err = f"{type(e).__name__}: {str(e) or type(e).__name__}"
        print(f"[slack] build failed: {err}")
        return SlackBuildResult(app=None, handler=None, error=err)

    register_all(slack_app)
    handler = SlackRequestHandler(slack_app)
    return SlackBuildResult(app=slack_app, handler=handler, error=None)
