from __future__ import annotations

import importlib
import pkgutil


def _iter_submodule_names(package_name: str) -> list[str]:
    """package_name 配下の全サブモジュール名を返す（再帰なし）"""
    package = importlib.import_module(package_name)
    names: list[str] = []
    for m in pkgutil.iter_modules(package.__path__, package.__name__ + "."):  # type: ignore[attr-defined]
        if m.ispkg:
            continue
        names.append(m.name)
    return names


def register_all(slack_app) -> None:  # noqa: ANN001
    """
    gemsrack.slack.commands / gemsrack.slack.events 配下の各モジュールに
    `register(slack_app)` があれば呼び出して登録する。
    """
    for pkg in ("gemsrack.slack.commands", "gemsrack.slack.events"):
        for mod_name in _iter_submodule_names(pkg):
            try:
                mod = importlib.import_module(mod_name)
            except Exception as e:
                print(f"[slack] failed to import {mod_name}: {type(e).__name__} {e}")
                continue

            register = getattr(mod, "register", None)
            if not callable(register):
                continue
            try:
                register(slack_app)
            except Exception as e:
                print(f"[slack] failed to register {mod_name}: {type(e).__name__} {e}")
