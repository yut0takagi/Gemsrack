from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Gem:
    team_id: str
    name: str
    # 表示用（ビジネス向け概要）
    summary: str

    # 互換用: 従来の「実行したら返すテキスト」
    body: str

    # AI Gem 用メタデータ
    system_prompt: str
    input_format: str
    output_format: str
    # Slack上で実行可能か（adminでON/OFF）
    enabled: bool
    created_by: str | None
    created_at: datetime
    updated_at: datetime

