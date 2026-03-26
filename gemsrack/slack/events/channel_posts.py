from __future__ import annotations

from flask import current_app


def _extract_team_id(*, body: dict, event: dict) -> str:
    team_id = (
        body.get("team_id")
        or (body.get("team") or {}).get("id")
        or event.get("team")
        or "unknown"
    )
    return str(team_id)


def register(slack_app) -> None:  # noqa: ANN001
    @slack_app.event("message")
    def handle_message_event(event, body):  # noqa: ANN001
        try:
            settings = current_app.extensions.get("settings")
            channel_ids = set(getattr(settings, "slack_log_channel_ids", ()) or ())
            if not channel_ids:
                return

            channel_id = str(event.get("channel") or "")
            if not channel_id or channel_id not in channel_ids:
                return

            store = current_app.extensions.get("channel_post_store")
            store_err = current_app.extensions.get("channel_post_store_error")
            if store is None:
                if store_err:
                    print(f"[channel_posts] store unavailable: {store_err}")
                return

            team_id = _extract_team_id(body=body or {}, event=event or {})
            store.record_post(team_id=team_id, channel_id=channel_id, event=dict(event or {}))
        except Exception as e:
            print(f"[channel_posts] failed to record message event: {type(e).__name__} {e}")
