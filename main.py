from __future__ import annotations

from gemsrack import create_app
from gemsrack.config import load_settings

app = create_app()

if __name__ == "__main__":
    settings = load_settings()
    app.run(host="0.0.0.0", port=settings.port)
