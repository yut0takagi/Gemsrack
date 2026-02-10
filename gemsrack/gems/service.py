from __future__ import annotations

from dataclasses import dataclass
import re
import shlex

from .formats import label_for_input, label_for_output
from .execute import execute_ai_gem, execute_ai_image_gem
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


def _strip_leading_public_flags(s: str) -> str:
    """
    入力本文の先頭に付いた `--public` / `-p` を取り除く（改行を保持したいので split しない）。
    例: "--public\\nhello" -> "hello"
    """
    out = s
    while True:
        t = out.lstrip()
        if t.startswith("--public") and (len(t) == 8 or t[8].isspace()):
            out = t[8:]
            continue
        if t.startswith("-p") and (len(t) == 2 or t[2].isspace()):
            out = t[2:]
            continue
        return out.lstrip()


def _raw_input_for_run(raw: str) -> tuple[str | None, str]:
    """
    `run <name> ...` の `...` を、改行含めてそのまま返す。
    戻り値: (name, user_input_raw)
    """
    m = re.match(r"^(?:run|exec)\s+([a-z0-9][a-z0-9_-]{0,31})([\s\S]*)$", raw.strip(), flags=re.I)
    if not m:
        return None, ""
    name = m.group(1)
    rest = m.group(2) or ""
    return name, _strip_leading_public_flags(rest)


def _raw_input_for_default_run(raw: str, name: str) -> str:
    """
    `<name> ...` の `...` を、改行含めてそのまま返す（先頭 public フラグは除去）。
    """
    m = re.match(rf"^{re.escape(name)}([\s\S]*)$", raw.strip(), flags=re.I)
    if not m:
        return ""
    rest = m.group(1) or ""
    return _strip_leading_public_flags(rest)


def handle_gem_command(
    *,
    store: GemStore,
    team_id: str,
    user_id: str | None,
    text: str,
    gemini=None,
    slack_client=None,  # Slack WebClient（画像生成時のアップロードに使用。任意）
    channel_id: str | None = None,
) -> GemCommandResult:  # noqa: ANN001
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
        # Slash command では改行が入りづらいが、モーダル経由では改行入力が来るので raw から復元する
        name2, user_input = _raw_input_for_run(raw)
        if name2 and name2.lower() == name.lower():
            pass
        else:
            user_input = " ".join(tokens[2:]).strip()
        try:
            n = validate_gem_name(name)
        except ValueError as e:
            return GemCommandResult(ok=False, message=str(e))

        gem = store.get(team_id=team_id, name=n)
        if not gem:
            return GemCommandResult(ok=False, message=f"Gem **{n}** が見つかりません。`/gem list` で確認できます。")
        if gem.body.strip():
            return GemCommandResult(ok=True, message=gem.body, public=public)
        # 画像生成 Gem の特例ハンドリング
        if (gem.output_format or "") == "image_url":
            ok, img_bytes, mime, msg = execute_ai_image_gem(gem=gem, user_input=user_input, gemini=gemini)
            if not ok or not img_bytes:
                return GemCommandResult(ok=False, message=msg or "画像生成に失敗しました。")

            # Slack にアップロード（公開: チャンネル / 非公開: DM）
            if slack_client is None:
                return GemCommandResult(ok=True, message="画像を生成しましたが、Slack へのアップロード権限がありません（管理者に `files:write` 追加を依頼してください）。")
            try:
                import io

                filename = f"{n}.png" if (mime or "").endswith("png") else f"{n}.jpg"
                target_channel = None
                if public and channel_id:
                    target_channel = channel_id
                elif user_id:
                    # DM チャンネルを開いて個別送信
                    opened = slack_client.conversations_open(users=user_id)
                    target_channel = (opened.get("channel") or {}).get("id")
                if not target_channel:
                    # 最後の手段として respond チャンネル（あれば）
                    target_channel = channel_id

                if hasattr(slack_client, "files_upload_v2"):
                    slack_client.files_upload_v2(
                        channel=target_channel,
                        filename=filename,
                        file=io.BytesIO(img_bytes),
                        title=f"Gem: {n}",
                    )
                else:  # 旧API互換
                    slack_client.files_upload(
                        channels=target_channel,
                        filename=filename,
                        file=io.BytesIO(img_bytes),
                        title=f"Gem: {n}",
                    )
                if public:
                    return GemCommandResult(ok=True, message=f"Gem `{n}` の画像をチャンネルにアップロードしました。", public=True)
                return GemCommandResult(ok=True, message=f"Gem `{n}` の画像をDMに送信しました。", public=False)
            except Exception as e:
                hint = ""
                err = type(e).__name__
                if "missing_scope" in str(e) or "not_allowed_token_type" in str(e):
                    hint = "\n必要スコープ: `files:write`（DM送信には `im:write`）。追加後、アプリを再インストール。"
                return GemCommandResult(ok=False, message=f"画像のアップロードに失敗しました: `{err}`{hint}")

        ok, msg = execute_ai_gem(gem=gem, user_input=user_input, gemini=gemini)
        return GemCommandResult(ok=ok, message=msg, public=public if ok else False)

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
    # `/gem <name> ...` も、モーダル経由では改行を保持したいので raw から復元する
    user_input = _raw_input_for_default_run(raw, sub)
    if not user_input:
        user_input = " ".join(tokens[1:]).strip()
    # 画像生成 Gem の特例ハンドリング（`/gem <name>` 形式）
    if (gem.output_format or "") == "image_url":
        ok, img_bytes, mime, msg = execute_ai_image_gem(gem=gem, user_input=user_input, gemini=gemini)
        if not ok or not img_bytes:
            return GemCommandResult(ok=False, message=msg or "画像生成に失敗しました。")
        if slack_client is None:
            return GemCommandResult(ok=True, message="画像を生成しましたが、Slack へのアップロード権限がありません（管理者に `files:write` 追加を依頼してください）。")
        try:
            import io

            filename = f"{n}.png" if (mime or "").endswith("png") else f"{n}.jpg"
            target_channel = None
            if public and channel_id:
                target_channel = channel_id
            elif user_id:
                opened = slack_client.conversations_open(users=user_id)
                target_channel = (opened.get("channel") or {}).get("id")
            if not target_channel:
                target_channel = channel_id

            if hasattr(slack_client, "files_upload_v2"):
                slack_client.files_upload_v2(
                    channel=target_channel,
                    filename=filename,
                    file=io.BytesIO(img_bytes),
                    title=f"Gem: {n}",
                )
            else:
                slack_client.files_upload(
                    channels=target_channel,
                    filename=filename,
                    file=io.BytesIO(img_bytes),
                    title=f"Gem: {n}",
                )
            if public:
                return GemCommandResult(ok=True, message=f"Gem `{n}` の画像をチャンネルにアップロードしました。", public=True)
            return GemCommandResult(ok=True, message=f"Gem `{n}` の画像をDMに送信しました。", public=False)
        except Exception as e:
            hint = ""
            err = type(e).__name__
            if "missing_scope" in str(e) or "not_allowed_token_type" in str(e):
                hint = "\n必要スコープ: `files:write`（DM送信には `im:write`）。追加後、アプリを再インストール。"
            return GemCommandResult(ok=False, message=f"画像のアップロードに失敗しました: `{err}`{hint}")

    ok, msg = execute_ai_gem(gem=gem, user_input=user_input, gemini=gemini)
    return GemCommandResult(ok=ok, message=msg, public=public if ok else False)


def _help() -> str:
    return (
        "使い方:\n"
        "- `/gem create <name> <body...>`: （互換）静的テキストGemの作成/更新\n"
        "- `/gem create <name> --summary ... --system ... --input ... --output ...`: AI Gem定義の作成/更新\n"
        "- `/gem create <name>`: モーダルで AI Gem定義を作成/更新\n"
        "- `/gem <name>` または `/gem run <name>`: Gem実行（静的Gemはbodyを返す）\n"
        "  - 入力が長い場合は `run <name>`（入力なし）でモーダルから複数行入力できます\n"
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
        parts.append(f"*入力形式*: {label_for_input(gem.input_format)}\n```{gem.input_format}```")
    if gem.output_format:
        parts.append(f"*出力形式*: {label_for_output(gem.output_format)}\n```{gem.output_format}```")
    if gem.body:
        parts.append("*（互換）静的テキスト*:\n```" + gem.body + "```")
    parts.append("\n実行ロジック（AI API 呼び出し）はこれから追加できます。")
    return "\n".join(parts)
