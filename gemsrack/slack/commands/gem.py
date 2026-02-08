from __future__ import annotations

import json

from ...gems.store import build_store
from ...gems.service import handle_gem_command
from ...gems.store import validate_gem_name


def register(slack_app) -> None:  # noqa: ANN001
    store = build_store()

    @slack_app.command("/gem")
    def gem_command(ack, respond, command, client):  # noqa: ANN001
        ack()
        team_id = command.get("team_id") or command.get("team_domain") or "unknown"
        user_id = command.get("user_id")
        text = command.get("text", "")

        # `/gem create <name>` のときはモーダルで入力できるようにする
        try:
            tokens = (text or "").strip().split()
        except Exception:
            tokens = []

        if len(tokens) >= 2 and tokens[0].lower() in ("create", "set") and len(tokens) == 2:
            name = tokens[1]
            try:
                n = validate_gem_name(name)
            except ValueError as e:
                respond(str(e))
                return

            trigger_id = command.get("trigger_id")
            channel_id = command.get("channel_id")
            if not trigger_id or not channel_id:
                respond("モーダル起動に必要な情報が足りません（trigger_id/channel_id）")
                return

            private_metadata = json.dumps(
                {
                    "team_id": team_id,
                    "name": n,
                    "user_id": user_id,
                    "channel_id": channel_id,
                }
            )

            client.views_open(
                trigger_id=trigger_id,
                view={
                    "type": "modal",
                    "callback_id": "gem_create_modal",
                    "private_metadata": private_metadata,
                    "title": {"type": "plain_text", "text": "Create Gem"},
                    "submit": {"type": "plain_text", "text": "Save"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "summary",
                            "optional": True,
                            "label": {"type": "plain_text", "text": "概要（1行）"},
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "value",
                                "placeholder": {"type": "plain_text", "text": "例: Marpスライドの叩き台を作る"},
                            },
                        },
                        {
                            "type": "input",
                            "block_id": "system",
                            "optional": True,
                            "label": {"type": "plain_text", "text": "システムプロンプト"},
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "value",
                                "multiline": True,
                                "placeholder": {"type": "plain_text", "text": "例: あなたは優秀なアシスタントです..."},
                            },
                        },
                        {
                            "type": "input",
                            "block_id": "input_format",
                            "optional": True,
                            "label": {"type": "plain_text", "text": "入力形式"},
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "value",
                                "multiline": True,
                                "placeholder": {"type": "plain_text", "text": "例: 箇条書き / JSON / フォーム項目..."},
                            },
                        },
                        {
                            "type": "input",
                            "block_id": "output_format",
                            "optional": True,
                            "label": {"type": "plain_text", "text": "出力形式"},
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "value",
                                "multiline": True,
                                "placeholder": {"type": "plain_text", "text": "例: Marp Markdown / 画像URL / JSON..."},
                            },
                        },
                        {
                            "type": "input",
                            "block_id": "body",
                            "optional": True,
                            "label": {"type": "plain_text", "text": "（任意）静的テキスト（互換）"},
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "value",
                                "multiline": True,
                                "placeholder": {"type": "plain_text", "text": "今すぐ返したい固定文言があれば"},
                            },
                        },
                    ],
                },
            )
            return

        result = handle_gem_command(store=store, team_id=team_id, user_id=user_id, text=text)

        if result.public:
            respond(result.message, response_type="in_channel")
        else:
            respond(result.message)

    @slack_app.view("gem_create_modal")
    def gem_create_modal(ack, body, view, client):  # noqa: ANN001
        ack()

        meta = {}
        try:
            meta = json.loads(view.get("private_metadata") or "{}")
        except Exception:
            meta = {}

        team_id = meta.get("team_id") or "unknown"
        name = meta.get("name") or "unknown"
        user_id = meta.get("user_id")
        channel_id = meta.get("channel_id")

        state = (view.get("state") or {}).get("values") or {}

        def _val(block_id: str) -> str:
            b = state.get(block_id) or {}
            a = b.get("value") or {}
            return (a.get("value") or "").strip()

        summary = _val("summary")
        system_prompt = _val("system")
        input_format = _val("input_format")
        output_format = _val("output_format")
        body_text = _val("body")

        store.upsert(
            team_id=team_id,
            name=name,
            summary=summary,
            body=body_text,
            system_prompt=system_prompt,
            input_format=input_format,
            output_format=output_format,
            created_by=user_id,
        )

        if channel_id and user_id:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"Gem `{name}` を保存しました。詳細: `/gem show {name}`",
            )

