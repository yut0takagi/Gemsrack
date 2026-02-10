from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    port: int
    slack_bot_token: str | None
    slack_signing_secret: str | None
    default_team_id: str


def load_settings() -> Settings:
    port = int(os.environ.get("PORT", "8080"))
    return Settings(
        port=port,
        slack_bot_token=os.environ.get("SLACK_BOT_TOKEN"),
        slack_signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
        # Slack外の閲覧UI用（単一ワークスペース想定のデフォルト）
        default_team_id=(os.environ.get("GEMSRACK_TEAM_ID") or os.environ.get("GEMSRACK_DEFAULT_TEAM_ID") or "local"),
    )
