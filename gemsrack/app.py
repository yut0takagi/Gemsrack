from __future__ import annotations

from flask import Flask

from .config import Settings, load_settings
from .gems.store import build_store
from .routes import api_bp, health_bp, slack_bp, web_bp
from .slack import SlackBuildResult, build_slack


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or load_settings()

    app = Flask(__name__)
    app.extensions["settings"] = settings

    # Gem store（SlackコマンドとWeb APIで共有）
    try:
        store = build_store()
        app.extensions["gem_store"] = store
        app.extensions["gem_store_error"] = None
    except Exception as e:
        # Cloud Run の場合は build_store 側で例外化され得る。ここはエラーを保持してAPIで返せるようにする。
        app.extensions["gem_store"] = None
        app.extensions["gem_store_error"] = f"{type(e).__name__}: {str(e) or type(e).__name__}"

    slack: SlackBuildResult = build_slack(settings)
    app.extensions["slack_handler"] = slack.handler
    app.extensions["slack_error"] = slack.error

    app.register_blueprint(health_bp)
    app.register_blueprint(slack_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)

    return app
