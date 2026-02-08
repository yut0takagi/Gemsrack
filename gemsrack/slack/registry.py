from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def _iter_submodules(package_name: str) -> list[ModuleType]:
    """package_name 配下の全サブモジュールを import して返す（再帰なし）"""
    package = importlib.import_module(package_name)
    modules: list[ModuleType] = []
    for m in pkgutil.iter_modules(package.__path__, package.__name__ + "."):  # type: ignore[attr-defined]
        if m.ispkg:
            continue
        modules.append(importlib.import_module(m.name))
    return modules


def register_all(slack_app) -> None:  # noqa: ANN001
    """
    gemsrack.slack.commands / gemsrack.slack.events 配下の各モジュールに
    `register(slack_app)` があれば呼び出して登録する。
    """
    for pkg in ("gemsrack.slack.commands", "gemsrack.slack.events"):
        for mod in _iter_submodules(pkg):
            register = getattr(mod, "register", None)
            if callable(register):
                register(slack_app)
