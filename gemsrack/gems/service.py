from __future__ import annotations

from dataclasses import dataclass
import shlex

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

    try:
        tokens = shlex.split(raw)
    except ValueError:
        tokens = raw.split()
    tokens, public = parse_public_flag(tokens)
    if not tokens:
        return GemCommandResult(ok=True, message=_help())

    sub = tokens[0].lower()

    if sub in ("help", "-h", "--help"):
        return GemCommandResult(ok=True, message=_help())

    if sub in ("create", "set"):
        if len(tokens) < 3:
            return GemCommandResult(ok=False, message="使い方: `/gem create <name> <body...>` または `/gem create <name> --summary ... --system ...`\n\n" + _help())
        name = tokens[1]

        # フラグ形式（AI Gem 用メタデータ）
        summary = ""
        system_prompt = ""
        input_format = ""
        output_format = ""

        rest = tokens[2:]
        if any(t.startswith("--") for t in rest):
            i = 0
            body_parts: list[str] = []
            while i < len(rest):
                t = rest[i]
                if t in ("--summary",):
                    i += 1
                    summary = rest[i] if i < len(rest) else ""
                elif t in ("--system", "--system-prompt"):
                    i += 1
                    system_prompt = rest[i] if i < len(rest) else ""
                elif t in ("--input", "--input-format"):
                    i += 1
                    input_format = rest[i] if i < len(rest) else ""
                elif t in ("--output", "--output-format"):
                    i += 1
                    output_format = rest[i] if i < len(rest) else ""
                else:
                    body_parts.append(t)
                i += 1

            # 互換のため、余った tokens は body として保存も可能
            body = " ".join(body_parts).strip()
        else:
            # 従来形式
            body = " ".join(rest)
        try:
            n = validate_gem_name(name)
        except ValueError as e:
            return GemCommandResult(ok=False, message=str(e))

        store.upsert(
            team_id=team_id,
            name=n,
            summary=summary,
            body=body,
            system_prompt=system_prompt,
            input_format=input_format,
            output_format=output_format,
            created_by=user_id,
        )
        if system_prompt or input_format or output_format or summary:
            return GemCommandResult(ok=True, message=f"Gem **{n}** を保存しました。詳細: `/gem show {n}`")
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
        if gem.body.strip():
            return GemCommandResult(ok=True, message=gem.body, public=public)
        return GemCommandResult(
            ok=True,
            message=_format_gem_definition(gem),
            public=False,
        )

    if sub == "list":
        gems = store.list(team_id=team_id, limit=50)
        if not gems:
            return GemCommandResult(ok=True, message="Gem はまだありません。作成: `/gem create <name> <body...>` または `/gem create <name> --summary ...`")
        lines = "\n".join([f"- `{g.name}` — {g.summary}" if g.summary else f"- `{g.name}`" for g in gems])
        return GemCommandResult(ok=True, message="利用可能な Gem:\n" + lines)

    if sub in ("show", "info"):
        if len(tokens) < 2:
            return GemCommandResult(ok=False, message="使い方: `/gem show <name>`\n\n" + _help())
        name = tokens[1]
        try:
            n = validate_gem_name(name)
        except ValueError as e:
            return GemCommandResult(ok=False, message=str(e))
        gem = store.get(team_id=team_id, name=n)
        if not gem:
            return GemCommandResult(ok=False, message=f"Gem **{n}** が見つかりません。")
        return GemCommandResult(ok=True, message=_format_gem_definition(gem))

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
    if gem.body.strip():
        return GemCommandResult(ok=True, message=gem.body, public=public)
    return GemCommandResult(ok=True, message=_format_gem_definition(gem), public=False)


def _help() -> str:
    return (
        "使い方:\n"
        "- `/gem create <name> <body...>`: （互換）静的テキストGemの作成/更新\n"
        "- `/gem create <name> --summary ... --system ... --input ... --output ...`: AI Gem定義の作成/更新\n"
        "- `/gem create <name>`: モーダルで AI Gem定義を作成/更新\n"
        "- `/gem <name>` または `/gem run <name>`: Gem実行（静的Gemはbodyを返す）\n"
        "- `/gem show <name>`: Gem定義の表示\n"
        "- `/gem list`: 一覧\n"
        "- `/gem delete <name>`: 削除\n"
        "- オプション: `--public`（実行結果をチャンネルに公開）\n"
        "\n"
        "例:\n"
        "- `/gem create hello おはようございます！`\n"
        "- `/gem hello`\n"
        '- `/gem create slide --summary "スライド案を作る" --system "あなたは..." --input "箇条書き" --output "Marp markdown"`\n'
        "- `/gem run hello --public`\n"
    )


def _format_gem_definition(gem) -> str:  # noqa: ANN001
    parts: list[str] = [f"*Gem*: `{gem.name}`"]
    if gem.summary:
        parts.append(f"*概要*: {gem.summary}")
    if gem.system_prompt:
        parts.append("*システムプロンプト*:\n```" + gem.system_prompt + "```")
    if gem.input_format:
        parts.append("*入力形式*:\n```" + gem.input_format + "```")
    if gem.output_format:
        parts.append("*出力形式*:\n```" + gem.output_format + "```")
    if gem.body:
        parts.append("*（互換）静的テキスト*:\n```" + gem.body + "```")
    parts.append("\n実行ロジック（AI API 呼び出し）はこれから追加できます。")
    return "\n".join(parts)

