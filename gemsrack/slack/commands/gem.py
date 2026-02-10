from __future__ import annotations

import json
import shlex
import threading

from flask import current_app
from slack_sdk.errors import SlackApiError, SlackRequestError

from ...ai import build_gemini_client
from ...gems.store import build_store
from ...gems.service import handle_gem_command, parse_public_flag
from ...gems.store import validate_gem_name
from ...gems.formats import INPUT_FORMATS, OUTPUT_FORMATS
from ...metrics.store import MetricsStore, NoopMetricsStore


def register(slack_app) -> None:  # noqa: ANN001
    gemini = build_gemini_client()
    _store = None
    _store_error: str | None = None
    _metrics: MetricsStore | None = None
    _metrics_error: str | None = None

    def _get_store():  # noqa: ANN001
        nonlocal _store, _store_error
        if _store is not None:
            return _store, None
        if _store_error is not None:
            return None, _store_error

        # Flask app が既に共有ストアを初期化していればそれを使う（特に memory backend でデータ共有するため）
        try:
            shared = current_app.extensions.get("gem_store")
            shared_err = current_app.extensions.get("gem_store_error")
            if shared is not None:
                _store = shared
                return _store, None
            if shared_err:
                _store_error = str(shared_err)
                return None, _store_error
        except Exception:
            pass

        try:
            _store = build_store()
            return _store, None
        except Exception as e:
            _store_error = f"{type(e).__name__}: {str(e) or type(e).__name__}"
            print(f"[gem] store init failed: {_store_error}")
            return None, _store_error

    def _get_metrics():  # noqa: ANN001
        nonlocal _metrics, _metrics_error
        if _metrics is not None:
            return _metrics, None
        if _metrics_error is not None:
            return NoopMetricsStore(), _metrics_error
        try:
            shared = current_app.extensions.get("metrics_store")
            shared_err = current_app.extensions.get("metrics_store_error")
            if shared is not None:
                _metrics = shared
                return _metrics, None
            if shared_err:
                _metrics_error = str(shared_err)
                return NoopMetricsStore(), _metrics_error
        except Exception:
            pass
        _metrics = NoopMetricsStore()
        _metrics_error = "metrics store is not initialized"
        return _metrics, _metrics_error

    @slack_app.command("/gem")
    def gem_command(ack, respond, command, client):  # noqa: ANN001
        ack()
        store, store_err = _get_store()
        if store is None:
            respond(
                "Gem の保存先（Firestore）の初期化に失敗したため、/gem を利用できません。\n"
                f"原因: `{store_err or 'unknown'}`\n"
                "\n"
                "対処:\n"
                "- Cloud Run の実行 Service Account に `roles/datastore.user` を付与\n"
                "- Firestore データベース（default）を作成/有効化\n"
                "- すぐ動かすだけなら `GEM_STORE_BACKEND=memory` を設定（※再デプロイで消えます）\n"
            )
            return
        team_id = command.get("team_id") or command.get("team_domain") or "unknown"
        user_id = command.get("user_id")
        text = command.get("text", "")
        trigger_id = command.get("trigger_id")
        channel_id = command.get("channel_id")

        # `/gem create <name>` のときはモーダルで入力できるようにする
        try:
            tokens = shlex.split((text or "").strip())
        except Exception:
            try:
                tokens = (text or "").strip().split()
            except Exception:
                tokens = []

        # `/gem run <name>` や `/gem <name>` で入力が無い場合は、改行対応のモーダルを開く
        try:
            tokens2, public_flag = parse_public_flag(tokens)
        except Exception:
            tokens2, public_flag = tokens, False

        def _open_run_modal(name: str, *, public: bool) -> bool:
            if not trigger_id or not channel_id:
                return False
            try:
                n = validate_gem_name(name)
            except ValueError:
                return False

            # 無効化されているGemはモーダルを開かない
            try:
                g = store.get(team_id=team_id, name=n)
                if g and not bool(getattr(g, "enabled", True)):
                    respond(f"Gem `{n}` は現在無効化されています（管理者に確認してください）。")
                    return True
            except Exception:
                pass

            private_metadata = json.dumps(
                {
                    "team_id": team_id,
                    "name": n,
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "public": public,
                }
            )

            public_opt = {"text": {"type": "plain_text", "text": "チャンネルに公開（in_channel）"}, "value": "public"}
            try:
                client.views_open(
                    trigger_id=trigger_id,
                    timeout=2,
                    view={
                        "type": "modal",
                        "callback_id": "gem_run_modal",
                        "private_metadata": private_metadata,
                        "title": {"type": "plain_text", "text": "Run Gem"},
                        "submit": {"type": "plain_text", "text": "Run"},
                        "close": {"type": "plain_text", "text": "Cancel"},
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*Gem*: `{n}`\n長文/改行入力に対応しています。",
                                },
                            },
                            {
                                "type": "input",
                                "block_id": "input",
                                "optional": True,
                                "label": {"type": "plain_text", "text": "入力（複数行OK）"},
                                "element": {
                                    "type": "plain_text_input",
                                    "action_id": "value",
                                    "multiline": True,
                                    "placeholder": {"type": "plain_text", "text": "ここに入力（改行もOK）"},
                                },
                            },
                            {
                                "type": "input",
                                "block_id": "public",
                                "optional": True,
                                "label": {"type": "plain_text", "text": "投稿先"},
                                "element": {
                                    "type": "checkboxes",
                                    "action_id": "value",
                                    "options": [public_opt],
                                    "initial_options": [public_opt] if public else [],
                                },
                            },
                        ],
                    },
                )
                return True
            except SlackApiError as e:
                data = getattr(e.response, "data", None)
                err = None
                if isinstance(data, dict):
                    err = data.get("error")
                err = err or "unknown_error"
                print(f"[gem] run modal open failed: {err} data={data}")
                hint = ""
                if err in ("invalid_trigger_id", "trigger_exchanged"):
                    hint = "\n`trigger_id` の期限切れの可能性があります。もう一度コマンドを実行してください。"
                respond(f"モーダル起動に失敗しました: `{err}`{hint}")
                return True
            except SlackRequestError as e:
                print(f"[gem] run modal request error: {e}")
                respond("モーダル起動に失敗しました: `network_error`（Slack API への通信エラー）")
                return True
            except Exception as e:
                print(f"[gem] run modal unexpected error: {type(e).__name__} {e}")
                respond(f"モーダル起動に失敗しました: `{type(e).__name__}`")
                return True

        # `run/exec` で入力が無い（= name まで）ならモーダル
        if len(tokens2) >= 2 and tokens2[0].lower() in ("run", "exec") and len(tokens2) == 2:
            if _open_run_modal(tokens2[1], public=public_flag):
                return

        # `/gem <name>` で入力が無い & AI/画像Gem（body空）の場合もモーダル
        if len(tokens2) == 1:
            maybe = tokens2[0].lower()
            if maybe not in ("help", "-h", "--help", "list", "show", "info", "create", "set", "delete", "del", "rm"):
                try:
                    n = validate_gem_name(maybe)
                    g = store.get(team_id=team_id, name=n)
                    if g and not g.body.strip():
                        if _open_run_modal(n, public=public_flag):
                            return
                except Exception:
                    pass

        if len(tokens) >= 2 and tokens[0].lower() in ("create", "set") and len(tokens) == 2:
            name = tokens[1]
            try:
                n = validate_gem_name(name)
            except ValueError as e:
                respond(str(e))
                return

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

            input_options = [
                {"text": {"type": "plain_text", "text": label}, "value": value}
                for value, label in INPUT_FORMATS
            ]
            output_options = [
                {"text": {"type": "plain_text", "text": label}, "value": value}
                for value, label in OUTPUT_FORMATS
            ]

            def _initial_option(options, value: str | None):  # noqa: ANN001
                if not value:
                    return None
                for opt in options:
                    if opt.get("value") == value:
                        return opt
                return None

            try:
                client.views_open(
                    trigger_id=trigger_id,
                    # ネットワーク遅延で 3 秒を超えると dispatch_failed になり得るため短めに設定
                    timeout=2,
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
                                    "type": "static_select",
                                    "action_id": "value",
                                    "placeholder": {"type": "plain_text", "text": "選択してください"},
                                    "options": input_options,
                                },
                            },
                            {
                                "type": "input",
                                "block_id": "output_format",
                                "optional": True,
                                "label": {"type": "plain_text", "text": "出力形式"},
                                "element": {
                                    "type": "static_select",
                                    "action_id": "value",
                                    "placeholder": {"type": "plain_text", "text": "選択してください"},
                                    "options": output_options,
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
            except SlackApiError as e:
                data = getattr(e.response, "data", None)
                err = None
                if isinstance(data, dict):
                    err = data.get("error")
                err = err or "unknown_error"
                print(f"[gem] views.open failed: {err} data={data}")
                hint = ""
                if err in ("missing_scope", "not_allowed_token_type"):
                    hint = "\n必要スコープ: `commands`（＋通知には `chat:write`）。追加後、アプリを再インストール。"
                elif err in ("invalid_trigger_id", "trigger_exchanged"):
                    hint = "\n`trigger_id` の期限切れの可能性があります（Cloud Run の cold start 回避に min instances=1 推奨）"
                elif err == "dispatch_failed":
                    hint = (
                        "\nSlack 側でモーダルの表示処理に失敗しました（多くは `trigger_id` 期限切れ/遅延が原因）。"
                        "\n- まずはもう一度 `/gem create <name>` を実行"
                        "\n- Cloud Run の cold start が疑わしい場合は **min instances=1**（＋必要なら CPU 常時割当）を推奨"
                        "\n- 代替: `/gem create <name> <body...>` または `--summary/--system/--input/--output` 形式で作成"
                    )
                elif err in ("invalid_auth", "not_authed", "account_inactive", "token_revoked"):
                    hint = "\n`SLACK_BOT_TOKEN` の設定を確認してください（xoxb-...）"
                respond(f"モーダル起動に失敗しました: `{err}`{hint}")
            except SlackRequestError as e:
                print(f"[gem] views.open request error: {e}")
                respond("モーダル起動に失敗しました: `network_error`（Slack API への通信エラー）")
            except Exception as e:
                print(f"[gem] views.open unexpected error: {type(e).__name__} {e}")
                respond(f"モーダル起動に失敗しました: `{type(e).__name__}`")
            return

        try:
            metrics_store, _ = _get_metrics()
            result = handle_gem_command(
                store=store,
                team_id=team_id,
                user_id=user_id,
                text=text,
                gemini=gemini,
                slack_client=client,
                channel_id=command.get("channel_id"),
                metrics_store=metrics_store,
            )
        except Exception as e:
            print(f"[gem] command error: {type(e).__name__} {e}")
            respond(f"処理中にエラーが発生しました: `{type(e).__name__}`")
            return

        if result.public:
            respond(result.message, response_type="in_channel")
        else:
            respond(result.message)

    @slack_app.view("gem_create_modal")
    def gem_create_modal(ack, body, view, client):  # noqa: ANN001
        # View submission は 3 秒以内に ack が必須。
        # Cloud Run の cold start / Firestore 遅延があってもタイムアウトしないよう、先に modal を閉じる。
        ack(response_action="clear")

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
            # plain_text_input: {"type":"plain_text_input","value":"..."}
            if isinstance(a, dict) and "value" in a:
                return (a.get("value") or "").strip()
            # static_select: {"type":"static_select","selected_option":{"value":"..."}}
            selected = (a or {}).get("selected_option") or {}
            return (selected.get("value") or "").strip()

        summary = _val("summary")
        system_prompt = _val("system")
        input_format = _val("input_format")
        output_format = _val("output_format")
        body_text = _val("body")

        def _save_and_notify() -> None:
            try:
                store, store_err = _get_store()
                if store is None:
                    if channel_id and user_id:
                        client.chat_postEphemeral(
                            channel=channel_id,
                            user=user_id,
                            text=(
                                "Gem の保存先（Firestore）の初期化に失敗したため、保存できません。\n"
                                f"原因: `{store_err or 'unknown'}`"
                            ),
                        )
                    return
                # ここでは遅くても良い（Slackへの ack は完了済み）
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
            except Exception as e:
                print(f"[gem] modal save failed: {type(e).__name__} {e}")
                # 失敗した場合もユーザーに通知（ベストエフォート）
                if channel_id and user_id:
                    try:
                        client.chat_postEphemeral(
                            channel=channel_id,
                            user=user_id,
                            text=f"Gem `{name}` の保存に失敗しました: `{type(e).__name__}`",
                        )
                    except Exception:
                        pass

        threading.Thread(target=_save_and_notify, daemon=True).start()

    @slack_app.view("gem_run_modal")
    def gem_run_modal(ack, body, view, client):  # noqa: ANN001
        ack(response_action="clear")

        meta = {}
        try:
            meta = json.loads(view.get("private_metadata") or "{}")
        except Exception:
            meta = {}

        team_id = meta.get("team_id") or "unknown"
        name = meta.get("name") or "unknown"
        user_id = meta.get("user_id")
        channel_id = meta.get("channel_id")
        meta_public = bool(meta.get("public"))

        state = (view.get("state") or {}).get("values") or {}

        def _plain(block_id: str) -> str:
            b = state.get(block_id) or {}
            a = b.get("value") or {}
            if isinstance(a, dict) and "value" in a:
                return (a.get("value") or "")
            return ""

        def _checked_public() -> bool:
            b = state.get("public") or {}
            a = b.get("value") or {}
            selected = (a or {}).get("selected_options") or []
            if not isinstance(selected, list):
                return False
            return any((opt or {}).get("value") == "public" for opt in selected if isinstance(opt, dict))

        user_input = _plain("input")
        public = _checked_public() or meta_public

        def _run_and_notify() -> None:
            try:
                store, store_err = _get_store()
                if store is None:
                    if channel_id and user_id:
                        client.chat_postEphemeral(
                            channel=channel_id,
                            user=user_id,
                            text=(
                                "Gem の保存先（Firestore）の初期化に失敗したため、実行できません。\n"
                                f"原因: `{store_err or 'unknown'}`"
                            ),
                        )
                    return

                # 改行を保持するため、本文は newline で渡す（service 側で raw から復元）
                cmd_text = f"run {name} " + ("--public\n" if public else "\n") + (user_input or "")
                result = handle_gem_command(
                    store=store,
                    team_id=team_id,
                    user_id=user_id,
                    text=cmd_text,
                    gemini=gemini,
                    slack_client=client,
                    channel_id=channel_id,
                    metrics_store=metrics_store,
                )

                if not channel_id or not user_id:
                    return
                if result.public:
                    client.chat_postMessage(channel=channel_id, text=result.message)
                else:
                    client.chat_postEphemeral(channel=channel_id, user=user_id, text=result.message)
            except Exception as e:
                print(f"[gem] run modal execution failed: {type(e).__name__} {e}")
                if channel_id and user_id:
                    try:
                        client.chat_postEphemeral(
                            channel=channel_id,
                            user=user_id,
                            text=f"Gem `{name}` の実行に失敗しました: `{type(e).__name__}`",
                        )
                    except Exception:
                        pass

        threading.Thread(target=_run_and_notify, daemon=True).start()
