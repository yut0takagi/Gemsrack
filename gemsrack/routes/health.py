from __future__ import annotations

from flask import Blueprint, Response

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health() -> Response:
    # Slack 側の設定有無に関わらず、コンテナ/Cloud Run の疎通確認に使えるよう常に 200 を返す
    return Response("ok\n", status=200)

