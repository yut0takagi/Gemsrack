from __future__ import annotations

import os

from flask import Flask

from .config import Settings, load_settings
from .gems.store import build_store
from .metrics import build_metrics_store
from .routes import admin_auth_bp, admin_bp, api_bp, health_bp, metrics_bp, slack_bp, web_bp
from .slack import SlackBuildResult, build_slack


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or load_settings()

    app = Flask(__name__)
    app.extensions["settings"] = settings
    app.secret_key = (
        os.environ.get("SECRET_KEY")
        or os.environ.get("FLASK_SECRET_KEY")
        or os.environ.get("ADMIN_SESSION_SECRET")
        or None
    )
    in_cloud_run = bool(os.environ.get("K_SERVICE"))
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=in_cloud_run,
    )

    # Gem store（SlackコマンドとWeb APIで共有）
    try:
        store = build_store()
        app.extensions["gem_store"] = store
        app.extensions["gem_store_error"] = None
    except Exception as e:
        # Cloud Run の場合は build_store 側で例外化され得る。ここはエラーを保持してAPIで返せるようにする。
        app.extensions["gem_store"] = None
        app.extensions["gem_store_error"] = f"{type(e).__name__}: {str(e) or type(e).__name__}"

    # Metrics store（Gem利用計測/KPI用）
    try:
        mstore = build_metrics_store()
        app.extensions["metrics_store"] = mstore
        app.extensions["metrics_store_error"] = None
    except Exception as e:
        app.extensions["metrics_store"] = None
        app.extensions["metrics_store_error"] = f"{type(e).__name__}: {str(e) or type(e).__name__}"

    slack: SlackBuildResult = build_slack(settings)
    app.extensions["slack_handler"] = slack.handler
    app.extensions["slack_error"] = slack.error

    app.register_blueprint(health_bp)
    app.register_blueprint(slack_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(admin_auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(web_bp)

    return app
