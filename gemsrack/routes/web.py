from __future__ import annotations

from pathlib import Path

from flask import Blueprint, Response, current_app, send_from_directory

web_bp = Blueprint("web", __name__)


def _dist_dir() -> Path:
    # Docker イメージ内では /app/web-dist に配置する
    base = current_app.root_path  # .../gemsrack
    cand = Path(base).parent / "web-dist"
    return cand


@web_bp.get("/")
def index() -> Response:
    dist = _dist_dir()
    index_html = dist / "index.html"
    if not index_html.exists():
        # フロント未ビルドでも API/Slack は動かせるようにする
        return Response(
            "Frontend is not built. Build the React app and include it in the container.\n",
            status=404,
            content_type="text/plain; charset=utf-8",
        )
    return send_from_directory(dist, "index.html")


@web_bp.get("/<path:path>")
def static_or_spa(path: str) -> Response:
    # /api, /slack, /health は他Blueprintに任せる（ここには来ない想定だが保険）
    if path.startswith(("api/", "slack/", "health")):
        return Response("not_found\n", status=404, content_type="text/plain; charset=utf-8")

    dist = _dist_dir()
    target = dist / path
    if target.exists() and target.is_file():
        return send_from_directory(dist, path)

    # SPA fallback（React Router を導入したくなった時も崩れないように）
    index_html = dist / "index.html"
    if index_html.exists():
        return send_from_directory(dist, "index.html")
    return Response(
        "Frontend is not built. Build the React app and include it in the container.\n",
        status=404,
        content_type="text/plain; charset=utf-8",
    )

