from __future__ import annotations

from dataclasses import dataclass

from .store import GemStore, validate_gem_name


@dataclass(frozen=True)
class GemCommandResult:
    ok: bool
    message: str
    public: bool = False


def parse_public_flag(tokens: list[str]) -> tuple[list[str], bool]:
    public = False
    rest: list[str] = []
    for t in tokens:
        if t in ("--public", "-p"):
            public = True
        else:
            rest.append(t)
    return rest, public


def handle_gem_command(*, store: GemStore, team_id: str, user_id: str | None, text: str) -> GemCommandResult:
    raw = (text or "").strip()
    if not raw:
        return GemCommandResult(
            ok=True,
            message=_help(),
        )

    tokens = raw.split()
    tokens, public = parse_public_flag(tokens)
    if not tokens:
        return GemCommandResult(ok=True, message=_help())

    sub = tokens[0].lower()

    if sub in ("help", "-h", "--help"):
        return GemCommandResult(ok=True, message=_help())

    if sub in ("create", "set"):
        if len(tokens) < 3:
            return GemCommandResult(ok=False, message="使い方: `/gem create <name> <body...>`\n\n" + _help())
        name = tokens[1]
        body = " ".join(tokens[2:])
        try:
            n = validate_gem_name(name)
        except ValueError as e:
            return GemCommandResult(ok=False, message=str(e))

        store.upsert(team_id=team_id, name=n, body=body, created_by=user_id)
        return GemCommandResult(ok=True, message=f"Gem **{n}** を保存しました。実行: `/gem {n}`")

    if sub in ("run", "exec"):
        if len(tokens) < 2:
            return GemCommandResult(ok=False, message="使い方: `/gem run <name>`\n\n" + _help())
        name = tokens[1]
        try:
            n = validate_gem_name(name)
        except ValueError as e:
            return GemCommandResult(ok=False, message=str(e))

        gem = store.get(team_id=team_id, name=n)
        if not gem:
            return GemCommandResult(ok=False, message=f"Gem **{n}** が見つかりません。`/gem list` で確認できます。")
        return GemCommandResult(ok=True, message=gem.body, public=public)

    if sub == "list":
        gems = store.list(team_id=team_id, limit=50)
        if not gems:
            return GemCommandResult(ok=True, message="Gem はまだありません。作成: `/gem create <name> <body...>`")
        lines = "\n".join([f"- `{g.name}`" for g in gems])
        return GemCommandResult(ok=True, message="利用可能な Gem:\n" + lines)

    if sub in ("delete", "del", "rm"):
        if len(tokens) < 2:
            return GemCommandResult(ok=False, message="使い方: `/gem delete <name>`\n\n" + _help())
        name = tokens[1]
        try:
            n = validate_gem_name(name)
        except ValueError as e:
            return GemCommandResult(ok=False, message=str(e))

        deleted = store.delete(team_id=team_id, name=n)
        if deleted:
            return GemCommandResult(ok=True, message=f"Gem **{n}** を削除しました。")
        return GemCommandResult(ok=False, message=f"Gem **{n}** は見つかりませんでした。")

    # サブコマンドなしで `/gem foo` を `/gem run foo` として扱う
    try:
        n = validate_gem_name(sub)
    except ValueError:
        return GemCommandResult(ok=False, message="不明なサブコマンドです。\n\n" + _help())

    gem = store.get(team_id=team_id, name=n)
    if not gem:
        return GemCommandResult(ok=False, message=f"Gem **{n}** が見つかりません。`/gem list` で確認できます。")
    return GemCommandResult(ok=True, message=gem.body, public=public)


def _help() -> str:
    return (
        "使い方:\n"
        "- `/gem create <name> <body...>`: Gem作成/更新\n"
        "- `/gem <name>` または `/gem run <name>`: Gem実行（bodyを返す）\n"
        "- `/gem list`: 一覧\n"
        "- `/gem delete <name>`: 削除\n"
        "- オプション: `--public`（実行結果をチャンネルに公開）\n"
        "\n"
        "例:\n"
        "- `/gem create hello おはようございます！`\n"
        "- `/gem hello`\n"
        "- `/gem run hello --public`\n"
    )

