from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, request, session

from ..gems.store import GemStore, validate_gem_name
from ..metrics.store import MetricsStore

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _require_admin() -> Response | None:
    # セッションログイン必須（Admin UI と完全分離）
    if bool(session.get("is_admin")):
        return None

    # secret_key が無いとセッションが使えないため、明示的に 503
    if not current_app.secret_key:
        resp = jsonify({"error": "admin_disabled", "message": "SECRET_KEY is not set"})
        resp.status_code = 503
        return resp

    resp = jsonify({"error": "unauthorized"})
    resp.status_code = 401
    return resp


def _store() -> GemStore:
    store = current_app.extensions.get("gem_store")
    if store is None:
        err = current_app.extensions.get("gem_store_error") or "Gem store is not initialized"
        raise RuntimeError(str(err))
    return store  # type: ignore[return-value]


def _metrics() -> MetricsStore:
    store = current_app.extensions.get("metrics_store")
    if store is None:
        err = current_app.extensions.get("metrics_store_error") or "Metrics store is not initialized"
        raise RuntimeError(str(err))
    return store  # type: ignore[return-value]


def _team_id() -> str:
    q = (request.args.get("team_id") or "").strip()
    if q:
        return q
    settings = current_app.extensions.get("settings")
    default_team_id = getattr(settings, "default_team_id", None) if settings else None
    return (default_team_id or "local").strip() or "local"


@admin_bp.get("/gems")
def admin_list_gems() -> Response:
    err = _require_admin()
    if err is not None:
        return err
    team_id = _team_id()
    store = _store()
    gems = store.list(team_id=team_id, limit=200)
    return jsonify(
        {
            "team_id": team_id,
            "count": len(gems),
            "gems": [
                {
                    "name": g.name,
                    "summary": g.summary,
                    "enabled": bool(getattr(g, "enabled", True)),
                    "input_format": g.input_format,
                    "output_format": g.output_format,
                    "updated_at": g.updated_at.isoformat(),
                }
                for g in gems
            ],
        }
    )


@admin_bp.patch("/gems/<name>")
def admin_patch_gem(name: str) -> Response:
    err = _require_admin()
    if err is not None:
        return err
    team_id = _team_id()
    try:
        n = validate_gem_name(name)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    body = request.get_json(silent=True) or {}
    if "enabled" not in body:
        return jsonify({"error": "enabled is required"}), 400
    enabled = bool(body.get("enabled"))

    store = _store()
    updated = store.set_enabled(team_id=team_id, name=n, enabled=enabled, updated_by=None)
    if not updated:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"team_id": team_id, "gem": {"name": updated.name, "enabled": updated.enabled}})


@admin_bp.get("/usage")
def admin_usage() -> Response:
    err = _require_admin()
    if err is not None:
        return err
    team_id = _team_id()
    days_raw = (request.args.get("days") or "").strip()
    try:
        days = int(days_raw) if days_raw else 30
    except Exception:
        days = 30
    days = max(1, min(days, 365))

    metrics = _metrics()
    summary = metrics.get_gem_usage_summary(team_id=team_id, days=days, limit=50)
    daily = metrics.list_gem_usage_daily(team_id=team_id, days=days)
    return jsonify(
        {
            "team_id": team_id,
            "days": days,
            "summary": {
                "from_date": summary.from_date,
                "to_date": summary.to_date,
                "total_count": summary.total_count,
                "public_count": summary.public_count,
                "ok_count": summary.ok_count,
                "error_count": summary.error_count,
                "by_day": summary.by_day,
                "top_gems": summary.top_gems,
            },
            "by_gem_day": [
                {
                    "date": r.date,
                    "gem_name": r.gem_name,
                    "count": r.count,
                    "public_count": r.public_count,
                    "ok_count": r.ok_count,
                    "error_count": r.error_count,
                }
                for r in daily
            ],
        }
    )

