from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Gem:
    team_id: str
    name: str
    body: str
    created_by: str | None
    created_at: datetime

