from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    port: int
    slack_bot_token: str | None
    slack_signing_secret: str | None


def load_settings() -> Settings:
    port = int(os.environ.get("PORT", "8080"))
    return Settings(
        port=port,
        slack_bot_token=os.environ.get("SLACK_BOT_TOKEN"),
        slack_signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    )
