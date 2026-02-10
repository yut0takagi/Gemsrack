from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, request

from ..metrics.store import MetricsStore

metrics_bp = Blueprint("metrics", __name__, url_prefix="/api/metrics")


def _metrics() -> MetricsStore:
    store = current_app.extensions.get("metrics_store")
    if store is None:
        err = current_app.extensions.get("metrics_store_error") or "Metrics store is not initialized"
        raise RuntimeError(str(err))
    return store  # type: ignore[return-value]


def _metrics_or_503() -> tuple[MetricsStore | None, Response | None]:
    try:
        return _metrics(), None
    except Exception as e:
        msg = str(e) or type(e).__name__
        resp = jsonify({"error": "metrics_unavailable", "message": msg})
        resp.status_code = 503
        return None, resp


def _team_id() -> str:
    q = (request.args.get("team_id") or "").strip()
    if q:
        return q
    settings = current_app.extensions.get("settings")
    default_team_id = getattr(settings, "default_team_id", None) if settings else None
    return (default_team_id or "local").strip() or "local"


@metrics_bp.get("/gem-usage")
def gem_usage() -> Response:
    days_raw = (request.args.get("days") or "").strip()
    limit_raw = (request.args.get("limit") or "").strip()
    try:
        days = int(days_raw) if days_raw else 30
    except Exception:
        days = 30
    try:
        limit = int(limit_raw) if limit_raw else 20
    except Exception:
        limit = 20

    days = max(1, min(days, 365))
    limit = max(1, min(limit, 100))

    store, err = _metrics_or_503()
    if err is not None:
        return err
    team_id = _team_id()
    s = store.get_gem_usage_summary(team_id=team_id, days=days, limit=limit)
    return jsonify(
        {
            "team_id": s.team_id,
            "days": s.days,
            "from_date": s.from_date,
            "to_date": s.to_date,
            "total_count": s.total_count,
            "public_count": s.public_count,
            "ok_count": s.ok_count,
            "error_count": s.error_count,
            "by_day": s.by_day,
            "top_gems": s.top_gems,
        }
    )

