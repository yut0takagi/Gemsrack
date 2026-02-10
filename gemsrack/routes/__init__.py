from .health import health_bp
from .slack import slack_bp
from .api import api_bp
from .web import web_bp

__all__ = ["health_bp", "slack_bp", "api_bp", "web_bp"]
