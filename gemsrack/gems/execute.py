from __future__ import annotations

import json

from ..ai.gemini import GeminiClient
from .formats import label_for_input, label_for_output


def execute_ai_gem(
    *,
    gem,
    user_input: str,
    gemini: GeminiClient | None,
) -> tuple[bool, str]:
    """
    Returns (ok, message).
    """
    if gemini is None:
        return False, "Gemini API が未設定です。Cloud Run の環境変数 `GEMINI_API_KEY` を設定してください。"

    if gem.output_format == "image_url":
        return False, "このGemは出力形式が画像ですが、画像生成はまだ未対応です（次対応: 画像生成モデル）。"

    # 入力の前処理（形式が指定されている場合のみ）
    prepared_input, err = _prepare_input(gem.input_format, user_input)
    if err:
        return False, err

    sys = (gem.system_prompt or "").strip() or "You are a helpful assistant."
    instruction = _build_user_instruction(
        summary=gem.summary or "",
        input_format=gem.input_format or "free_text",
        output_format=gem.output_format or "plain_text",
        prepared_input=prepared_input,
    )

    response_mime_type = None
    if gem.output_format == "json":
        response_mime_type = "application/json"
    elif gem.output_format in ("plain_text", "free_text"):
        response_mime_type = "text/plain"
    # markdown/marp_markdown は text/plain でOK（Slack/Marpの都合上）

    out = gemini.generate_text(
        system_instruction=sys,
        user_text=instruction,
        response_mime_type=response_mime_type,
    )

    ok, formatted = _postprocess_output(gem.output_format, out)
    return ok, formatted


def _build_user_instruction(*, summary: str, input_format: str, output_format: str, prepared_input: str) -> str:
    lines: list[str] = []
    if summary:
        lines.append(f"Task summary: {summary}")
    lines.append(f"Input format: {label_for_input(input_format)} ({input_format})")
    lines.append(f"Output format: {label_for_output(output_format)} ({output_format})")
    lines.append("")
    lines.append("INPUT:")
    lines.append(prepared_input)
    lines.append("")

    # 出力強制
    if output_format == "json":
        lines.append("Return ONLY valid JSON. No markdown, no code fences, no comments.")
    elif output_format == "marp_markdown":
        lines.append("Return ONLY Marp markdown for slides. Include YAML frontmatter with `marp: true`.")
    else:
        lines.append("Return the output in the specified format.")

    return "\n".join(lines)


def _prepare_input(input_format: str, user_input: str) -> tuple[str, str | None]:
    raw = (user_input or "").strip()
    if not raw:
        return "", "入力が空です。`/gem run <name> <入力...>` のように入力を渡してください。"

    if not input_format or input_format == "free_text":
        return raw, None
    if input_format == "bullet_points":
        return raw, None
    if input_format == "url_list":
        urls = [u for u in raw.replace(",", "\n").split() if u]
        if not urls:
            return "", "URL一覧として解釈できませんでした。URL を空白区切り/改行で渡してください。"
        return "\n".join([f"- {u}" for u in urls]), None
    if input_format == "json":
        try:
            obj = json.loads(raw)
        except Exception:
            return "", "入力形式が JSON です。正しい JSON を渡してください（例: `{ \"title\": \"...\" }`）。"
        return json.dumps(obj, ensure_ascii=False, indent=2), None
    if input_format == "slack_thread_url":
        return "", "入力形式が Slack スレッドURLですが、スレッド取得は未実装です（次対応）。"

    # 未知の形式はそのまま渡す（将来互換）
    return raw, None


def _postprocess_output(output_format: str, out: str) -> tuple[bool, str]:
    text = (out or "").strip()
    if not output_format or output_format in ("plain_text", "markdown"):
        return True, _truncate(text)

    if output_format == "json":
        try:
            obj = json.loads(text)
        except Exception:
            return False, _truncate("JSONとして解析できませんでした。モデル出力:\n```" + text + "```")
        pretty = json.dumps(obj, ensure_ascii=False, indent=2)
        return True, _truncate("```" + pretty + "```")

    if output_format == "marp_markdown":
        # ざっくり検証（最低限）
        if "marp: true" not in text[:400]:
            text = "---\nmarp: true\n---\n\n" + text
        return True, _truncate(text)

    return True, _truncate(text)


def _truncate(text: str, limit: int = 3500) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n...(truncated)"

