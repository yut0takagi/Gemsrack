from .health import health_bp
from .slack import slack_bp
from .api import api_bp
from .web import web_bp
from .metrics import metrics_bp
from .admin import admin_bp
from .admin_auth import admin_auth_bp

__all__ = ["health_bp", "slack_bp", "api_bp", "web_bp", "metrics_bp", "admin_bp", "admin_auth_bp"]
