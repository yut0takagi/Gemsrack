from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone


class ChannelPostStore(ABC):
    @abstractmethod
    def record_post(
        self,
        *,
        team_id: str,
        channel_id: str,
        event: dict,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_posts(
        self,
        *,
        team_id: str,
        channel_id: str,
        limit: int = 50,
    ) -> list[dict]:
        raise NotImplementedError


class NoopChannelPostStore(ChannelPostStore):
    def record_post(
        self,
        *,
        team_id: str,
        channel_id: str,
        event: dict,
    ) -> None:
        return

    def list_posts(
        self,
        *,
        team_id: str,
        channel_id: str,
        limit: int = 50,
    ) -> list[dict]:
        return []


class InMemoryChannelPostStore(ChannelPostStore):
    def __init__(self) -> None:
        # key: (team_id, channel_id)
        self._events: dict[tuple[str, str], list[dict]] = {}

    def record_post(
        self,
        *,
        team_id: str,
        channel_id: str,
        event: dict,
    ) -> None:
        key = (team_id, channel_id)
        rows = self._events.get(key, [])
        rows.append(
            {
                "recorded_at": datetime.now(timezone.utc),
                "event": dict(event),
            }
        )
        self._events[key] = rows

    def list_posts(
        self,
        *,
        team_id: str,
        channel_id: str,
        limit: int = 50,
    ) -> list[dict]:
        limit = max(1, min(limit, 200))
        rows = list(self._events.get((team_id, channel_id), []))
        rows.sort(key=lambda x: x.get("recorded_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        out: list[dict] = []
        for row in rows[:limit]:
            recorded_at = row.get("recorded_at")
            if isinstance(recorded_at, datetime):
                recorded_at_txt = recorded_at.isoformat()
            else:
                recorded_at_txt = None
            event = row.get("event") if isinstance(row.get("event"), dict) else {}
            out.append(
                {
                    "recorded_at": recorded_at_txt,
                    "event_ts": str(event.get("event_ts") or ""),
                    "ts": str(event.get("ts") or ""),
                    "channel_id": str(channel_id),
                    "user": str(event.get("user") or ""),
                    "subtype": str(event.get("subtype") or ""),
                    "text": str(event.get("text") or ""),
                    "event": event,
                }
            )
        return out


class FirestoreChannelPostStore(ChannelPostStore):
    def __init__(self, *, project_id: str | None = None) -> None:
        self._project_id = (
            project_id
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCP_PROJECT")
            or os.environ.get("GCLOUD_PROJECT")
        )
        from google.cloud import firestore  # type: ignore

        if self._project_id:
            self._client = firestore.Client(project=self._project_id)
        else:
            self._client = firestore.Client()

    def _messages_col(self, *, team_id: str, channel_id: str):
        # workspaces/{team_id}/channel_posts/{channel_id}/messages/{doc_id}
        return (
            self._client.collection("workspaces")
            .document(team_id)
            .collection("channel_posts")
            .document(channel_id)
            .collection("messages")
        )

    @staticmethod
    def _doc_id(event: dict) -> str:
        event_ts = str(event.get("event_ts") or "")
        ts = str(event.get("ts") or "")
        msg_ts = str((event.get("message") or {}).get("ts") or "")
        raw = event_ts or ts or msg_ts or datetime.now(timezone.utc).isoformat()
        return raw.replace(".", "_").replace(":", "_")

    def record_post(
        self,
        *,
        team_id: str,
        channel_id: str,
        event: dict,
    ) -> None:
        now = datetime.now(timezone.utc)
        subtype = str(event.get("subtype") or "")
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        previous_message = (
            event.get("previous_message") if isinstance(event.get("previous_message"), dict) else {}
        )

        payload = {
            "team_id": team_id,
            "channel_id": channel_id,
            "type": str(event.get("type") or "message"),
            "subtype": subtype,
            "event_ts": str(event.get("event_ts") or ""),
            "ts": str(event.get("ts") or ""),
            "thread_ts": str(event.get("thread_ts") or ""),
            "user": str(event.get("user") or ""),
            "bot_id": str(event.get("bot_id") or ""),
            "text": str(event.get("text") or ""),
            "message_user": str(message.get("user") or ""),
            "message_bot_id": str(message.get("bot_id") or ""),
            "message_text": str(message.get("text") or ""),
            "message_ts": str(message.get("ts") or ""),
            "previous_message_text": str(previous_message.get("text") or ""),
            "previous_message_ts": str(previous_message.get("ts") or ""),
            "recorded_at": now,
            "event": event,
        }

        doc_id = self._doc_id(event)
        self._messages_col(team_id=team_id, channel_id=channel_id).document(doc_id).set(payload, merge=True)

    def list_posts(
        self,
        *,
        team_id: str,
        channel_id: str,
        limit: int = 50,
    ) -> list[dict]:
        limit = max(1, min(limit, 200))
        snaps = (
            self._messages_col(team_id=team_id, channel_id=channel_id)
            .order_by("recorded_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        out: list[dict] = []
        for s in snaps:
            d = s.to_dict() or {}
            recorded_at = d.get("recorded_at")
            if isinstance(recorded_at, datetime):
                recorded_at_txt = recorded_at.isoformat()
            else:
                recorded_at_txt = None
            out.append(
                {
                    "recorded_at": recorded_at_txt,
                    "event_ts": str(d.get("event_ts") or ""),
                    "ts": str(d.get("ts") or ""),
                    "channel_id": str(d.get("channel_id") or channel_id),
                    "user": str(d.get("user") or ""),
                    "subtype": str(d.get("subtype") or ""),
                    "text": str(d.get("text") or ""),
                    "event": d.get("event") if isinstance(d.get("event"), dict) else {},
                }
            )
        return out


def build_channel_post_store() -> ChannelPostStore:
    """
    `CHANNEL_POST_STORE_BACKEND` で保存先を選ぶ:
    - `firestore`: Firestore を必須化（失敗時は例外）
    - `memory`: インメモリ
    - `none`: 無効化（Noop）
    - `auto`(既定): Firestore を試し、失敗時はローカルのみ memory にフォールバック
    """
    backend = (os.environ.get("CHANNEL_POST_STORE_BACKEND") or "auto").strip().lower()
    if backend in ("none", "noop", "off", "false"):
        return NoopChannelPostStore()
    if backend == "memory":
        return InMemoryChannelPostStore()
    if backend == "firestore":
        return FirestoreChannelPostStore()

    if backend != "auto":
        raise RuntimeError("CHANNEL_POST_STORE_BACKEND は `auto` / `firestore` / `memory` / `none` のいずれかにしてください")

    in_cloud_run = bool(os.environ.get("K_SERVICE"))
    try:
        return FirestoreChannelPostStore()
    except Exception as e:
        if in_cloud_run:
            detail = (str(e) or type(e).__name__).strip().replace("\n", " ")
            detail = detail[:200]
            raise RuntimeError(
                "Cloud Run で Firestore（channel posts）を初期化できません。"
                " `CHANNEL_POST_STORE_BACKEND=firestore` と Firestore 権限/認証設定を確認してください。"
                f" (原因: {type(e).__name__}: {detail})"
            ) from e
        print(f"[channel_posts] Firestore unavailable; falling back to memory store: {type(e).__name__} {e}")
        return InMemoryChannelPostStore()
