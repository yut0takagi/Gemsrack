from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from flask import Blueprint, Response, current_app, jsonify, request

from ..gems.store import GemStore, validate_gem_name

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _dt(v: datetime | None) -> str | None:
    if v is None:
        return None
    # ISO 8601 (例: 2026-02-10T12:34:56.789+00:00)
    return v.isoformat()


def _store() -> GemStore:
    store = current_app.extensions.get("gem_store")
    if store is None:
        err = current_app.extensions.get("gem_store_error") or "Gem store is not initialized"
        raise RuntimeError(str(err))
    return store  # type: ignore[return-value]

def _store_or_503() -> tuple[GemStore | None, Response | None]:
    try:
        return _store(), None
    except Exception as e:
        msg = str(e) or type(e).__name__
        resp = jsonify({"error": "store_unavailable", "message": msg})
        resp.status_code = 503
        return None, resp


def _team_id() -> str:
    # Slack以外のUI/APIでは team_id が自明でないので、
    # クエリ指定 or 設定のデフォルトに寄せる（未指定なら "local"）。
    q = (request.args.get("team_id") or "").strip()
    if q:
        return q
    settings = current_app.extensions.get("settings")
    default_team_id = getattr(settings, "default_team_id", None) if settings else None
    return (default_team_id or "local").strip() or "local"


def _serialize_gem(gem, *, include_body: bool) -> dict:  # noqa: ANN001
    d = asdict(gem)
    d["created_at"] = _dt(gem.created_at)
    d["updated_at"] = _dt(gem.updated_at)
    if not include_body:
        d.pop("body", None)
        d.pop("system_prompt", None)
    return d


@api_bp.get("/gems")
def list_gems() -> Response:
    limit_raw = (request.args.get("limit") or "").strip()
    try:
        limit = int(limit_raw) if limit_raw else 200
    except Exception:
        limit = 200
    limit = max(1, min(limit, 200))

    store, err = _store_or_503()
    if err is not None:
        return err
    team_id = _team_id()
    gems = store.list(team_id=team_id, limit=limit)
    return jsonify(
        {
            "team_id": team_id,
            "count": len(gems),
            "gems": [_serialize_gem(g, include_body=False) for g in gems],
        }
    )


@api_bp.get("/gems/<name>")
def get_gem(name: str) -> Response:
    store, err = _store_or_503()
    if err is not None:
        return err
    team_id = _team_id()
    try:
        n = validate_gem_name(name)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    gem = store.get(team_id=team_id, name=n)
    if not gem:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"team_id": team_id, "gem": _serialize_gem(gem, include_body=True)})

