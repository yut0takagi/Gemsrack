from __future__ import annotations

from flask import Flask

from .config import Settings, load_settings
from .routes import health_bp, slack_bp
from .slack import SlackBuildResult, build_slack


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or load_settings()

    app = Flask(__name__)

    slack: SlackBuildResult = build_slack(settings)
    app.extensions["slack_handler"] = slack.handler
    app.extensions["slack_error"] = slack.error

    app.register_blueprint(health_bp)
    app.register_blueprint(slack_bp)

    return app
