from __future__ import annotations

import os

from flask import Blueprint, Response, jsonify, request, session

admin_auth_bp = Blueprint("admin_auth", __name__, url_prefix="/api/admin")


def _admin_password() -> str | None:
    p = (os.environ.get("ADMIN_PASSWORD") or "").strip()
    return p or None


def _admin_enabled() -> bool:
    return _admin_password() is not None


@admin_auth_bp.get("/me")
def me() -> Response:
    if not _admin_enabled():
        resp = jsonify({"admin": False, "enabled": False})
        resp.status_code = 503
        return resp
    # secret_key が無いとセッションが使えないため、明示的に 503
    #（app.secret_key は create_app で設定される）
    from flask import current_app

    if not current_app.secret_key:
        resp = jsonify({"admin": False, "enabled": False, "error": "SECRET_KEY is not set"})
        resp.status_code = 503
        return resp
    return jsonify({"admin": bool(session.get("is_admin")), "enabled": True})


@admin_auth_bp.post("/login")
def login() -> Response:
    pw = _admin_password()
    if not pw:
        resp = jsonify({"error": "admin_disabled", "message": "ADMIN_PASSWORD is not set"})
        resp.status_code = 503
        return resp
    from flask import current_app

    if not current_app.secret_key:
        resp = jsonify({"error": "admin_disabled", "message": "SECRET_KEY is not set"})
        resp.status_code = 503
        return resp

    body = request.get_json(silent=True) or {}
    got = str(body.get("password") or "")
    if got != pw:
        resp = jsonify({"error": "unauthorized"})
        resp.status_code = 401
        return resp

    session["is_admin"] = True
    return jsonify({"ok": True})


@admin_auth_bp.post("/logout")
def logout() -> Response:
    session.clear()
    return jsonify({"ok": True})

