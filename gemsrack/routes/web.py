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

@web_bp.get("/admin")
@web_bp.get("/admin/")
def admin_index() -> Response:
    dist = _dist_dir()
    admin_html = dist / "admin" / "index.html"
    if not admin_html.exists():
        return Response(
            "Admin frontend is not built. Build the React app and include it in the container.\n",
            status=404,
            content_type="text/plain; charset=utf-8",
        )
    return send_from_directory(dist, "admin/index.html")


@web_bp.get("/<path:path>")
def static_or_spa(path: str) -> Response:
    # /api, /slack, /health は他Blueprintに任せる（ここには来ない想定だが保険）
    if path.startswith(("api/", "slack/", "health")):
        return Response("not_found\n", status=404, content_type="text/plain; charset=utf-8")

    dist = _dist_dir()
    target = dist / path
    if target.exists() and target.is_file():
        return send_from_directory(dist, path)

    # /admin 配下は admin/index.html にフォールバック（公開UIと分離）
    if path == "admin" or path.startswith("admin/"):
        admin_html = dist / "admin" / "index.html"
        if admin_html.exists():
            return send_from_directory(dist, "admin/index.html")
        return Response(
            "Admin frontend is not built. Build the React app and include it in the container.\n",
            status=404,
            content_type="text/plain; charset=utf-8",
        )

    # SPA fallback（React Router を導入したくなった時も崩れないように）
    index_html = dist / "index.html"
    if index_html.exists():
        return send_from_directory(dist, "index.html")
    return Response(
        "Frontend is not built. Build the React app and include it in the container.\n",
        status=404,
        content_type="text/plain; charset=utf-8",
    )

