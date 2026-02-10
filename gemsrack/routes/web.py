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

def _admin_html(kind: str) -> Path:
    # kind: "login" | "dashboard"
    dist = _dist_dir()
    return dist / "admin" / kind / "index.html"


@web_bp.get("/admin/login")
@web_bp.get("/admin/login/")
def admin_login() -> Response:
    dist = _dist_dir()
    html = _admin_html("login")
    if not html.exists():
        return Response(
            "Admin login frontend is not built. Build the React app and include it in the container.\n",
            status=404,
            content_type="text/plain; charset=utf-8",
        )
    return send_from_directory(dist, "admin/login/index.html")


@web_bp.get("/admin/dashboard")
@web_bp.get("/admin/dashboard/")
def admin_dashboard() -> Response:
    dist = _dist_dir()
    html = _admin_html("dashboard")
    if not html.exists():
        return Response(
            "Admin dashboard frontend is not built. Build the React app and include it in the container.\n",
            status=404,
            content_type="text/plain; charset=utf-8",
        )
    return send_from_directory(dist, "admin/dashboard/index.html")


@web_bp.get("/<path:path>")
def static_or_spa(path: str) -> Response:
    # /api, /slack, /health は他Blueprintに任せる（ここには来ない想定だが保険）
    if path.startswith(("api/", "slack/", "health")):
        return Response("not_found\n", status=404, content_type="text/plain; charset=utf-8")

    dist = _dist_dir()
    target = dist / path
    if target.exists() and target.is_file():
        return send_from_directory(dist, path)

    # /admin 配下は login/dashboard にのみルーティング（完全分離）
    if path == "admin" or path == "admin/":
        # 明示的に login へ誘導（相対/絶対の混乱を避けるため 302）
        resp = Response("", status=302)
        resp.headers["Location"] = "/admin/login"
        return resp

    if path == "admin/login" or path.startswith("admin/login/"):
        html = _admin_html("login")
        if html.exists():
            return send_from_directory(dist, "admin/login/index.html")
        return Response(
            "Admin login frontend is not built. Build the React app and include it in the container.\n",
            status=404,
            content_type="text/plain; charset=utf-8",
        )

    if path == "admin/dashboard" or path.startswith("admin/dashboard/"):
        html = _admin_html("dashboard")
        if html.exists():
            return send_from_directory(dist, "admin/dashboard/index.html")
        return Response(
            "Admin dashboard frontend is not built. Build the React app and include it in the container.\n",
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

