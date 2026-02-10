from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from .models import Gem

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


def validate_gem_name(name: str) -> str:
    n = name.strip().lower()
    if not _NAME_RE.match(n):
        raise ValueError("Gem名は `a-z 0-9 _ -` で1〜32文字（先頭は英数字）にしてください")
    return n


class GemStore(ABC):
    @abstractmethod
    def upsert(
        self,
        *,
        team_id: str,
        name: str,
        summary: str = "",
        body: str = "",
        system_prompt: str = "",
        input_format: str = "",
        output_format: str = "",
        created_by: str | None,
    ) -> Gem:
        raise NotImplementedError

    @abstractmethod
    def get(self, *, team_id: str, name: str) -> Gem | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, *, team_id: str, name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list(self, *, team_id: str, limit: int = 50) -> list[Gem]:
        raise NotImplementedError


class InMemoryGemStore(GemStore):
    def __init__(self) -> None:
        self._data: dict[tuple[str, str], Gem] = {}

    def upsert(
        self,
        *,
        team_id: str,
        name: str,
        summary: str = "",
        body: str = "",
        system_prompt: str = "",
        input_format: str = "",
        output_format: str = "",
        created_by: str | None,
    ) -> Gem:
        n = validate_gem_name(name)
        now = datetime.now(timezone.utc)
        gem = Gem(
            team_id=team_id,
            name=n,
            summary=summary.strip(),
            body=body.strip(),
            system_prompt=system_prompt.strip(),
            input_format=input_format.strip(),
            output_format=output_format.strip(),
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self._data[(team_id, n)] = gem
        return gem

    def get(self, *, team_id: str, name: str) -> Gem | None:
        n = validate_gem_name(name)
        return self._data.get((team_id, n))

    def delete(self, *, team_id: str, name: str) -> bool:
        n = validate_gem_name(name)
        return self._data.pop((team_id, n), None) is not None

    def list(self, *, team_id: str, limit: int = 50) -> list[Gem]:
        gems = [g for (tid, _), g in self._data.items() if tid == team_id]
        gems.sort(key=lambda g: g.created_at, reverse=True)
        return gems[: max(1, min(limit, 200))]


class FirestoreGemStore(GemStore):
    def __init__(self, *, project_id: str | None = None) -> None:
        self._project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        if not self._project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT が見つかりません（Cloud Run では自動設定されます）")

        from google.cloud import firestore  # 遅延import（ローカルで依存なしでも動くため）

        self._client = firestore.Client(project=self._project_id)

    def _doc_ref(self, *, team_id: str, name: str):
        n = validate_gem_name(name)
        # workspaces/{team_id}/gems/{name}
        return (
            self._client.collection("workspaces")
            .document(team_id)
            .collection("gems")
            .document(n)
        )

    def upsert(
        self,
        *,
        team_id: str,
        name: str,
        summary: str = "",
        body: str = "",
        system_prompt: str = "",
        input_format: str = "",
        output_format: str = "",
        created_by: str | None,
    ) -> Gem:
        ref = self._doc_ref(team_id=team_id, name=name)
        n = validate_gem_name(name)
        now = datetime.now(timezone.utc)
        payload = {
            "team_id": team_id,
            "name": n,
            "summary": summary.strip(),
            "body": body.strip(),
            "system_prompt": system_prompt.strip(),
            "input_format": input_format.strip(),
            "output_format": output_format.strip(),
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }
        ref.set(payload, merge=True)
        return Gem(
            team_id=team_id,
            name=n,
            summary=payload["summary"],
            body=payload["body"],
            system_prompt=payload["system_prompt"],
            input_format=payload["input_format"],
            output_format=payload["output_format"],
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    def get(self, *, team_id: str, name: str) -> Gem | None:
        ref = self._doc_ref(team_id=team_id, name=name)
        snap = ref.get()
        if not snap.exists:
            return None
        d = snap.to_dict() or {}
        created_at = d.get("created_at")
        if not isinstance(created_at, datetime):
            created_at = datetime.now(timezone.utc)
        updated_at = d.get("updated_at")
        if not isinstance(updated_at, datetime):
            updated_at = created_at
        return Gem(
            team_id=team_id,
            name=d.get("name") or validate_gem_name(name),
            summary=d.get("summary") or "",
            body=d.get("body") or "",
            system_prompt=d.get("system_prompt") or "",
            input_format=d.get("input_format") or "",
            output_format=d.get("output_format") or "",
            created_by=d.get("created_by"),
            created_at=created_at,
            updated_at=updated_at,
        )

    def delete(self, *, team_id: str, name: str) -> bool:
        ref = self._doc_ref(team_id=team_id, name=name)
        snap = ref.get()
        if not snap.exists:
            return False
        ref.delete()
        return True

    def list(self, *, team_id: str, limit: int = 50) -> list[Gem]:
        limit = max(1, min(limit, 200))
        col = self._client.collection("workspaces").document(team_id).collection("gems")
        snaps = col.order_by("updated_at", direction="DESCENDING").limit(limit).stream()
        out: list[Gem] = []
        for s in snaps:
            d = s.to_dict() or {}
            created_at = d.get("created_at")
            if not isinstance(created_at, datetime):
                created_at = datetime.now(timezone.utc)
            updated_at = d.get("updated_at")
            if not isinstance(updated_at, datetime):
                updated_at = created_at
            out.append(
                Gem(
                    team_id=team_id,
                    name=str(d.get("name") or s.id),
                    summary=str(d.get("summary") or ""),
                    body=str(d.get("body") or ""),
                    system_prompt=str(d.get("system_prompt") or ""),
                    input_format=str(d.get("input_format") or ""),
                    output_format=str(d.get("output_format") or ""),
                    created_by=d.get("created_by"),
                    created_at=created_at,
                    updated_at=updated_at,
                )
            )
        return out


def build_store() -> GemStore:
    """
    `GEM_STORE_BACKEND` で保存先を選ぶ:
    - `firestore`: Firestore を必須化（失敗時は例外）
    - `memory`: インメモリ（再起動/再デプロイで消える）
    - `auto`(既定): Firestore を試し、失敗時はローカルのみ memory にフォールバック

    Cloud Run では `auto` 時も Firestore 失敗で例外にし、
    永続化の取りこぼし（更新時に Gem が消える）を防ぐ。
    """
    backend = (os.environ.get("GEM_STORE_BACKEND") or "auto").strip().lower()

    if backend == "memory":
        return InMemoryGemStore()
    if backend == "firestore":
        return FirestoreGemStore()

    if backend != "auto":
        raise RuntimeError("GEM_STORE_BACKEND は `auto` / `firestore` / `memory` のいずれかにしてください")

    in_cloud_run = bool(os.environ.get("K_SERVICE"))
    try:
        return FirestoreGemStore()
    except Exception as e:
        if in_cloud_run:
            detail = (str(e) or type(e).__name__).strip().replace("\n", " ")
            detail = detail[:200]
            raise RuntimeError(
                "Cloud Run で Firestore を初期化できません。"
                " `GEM_STORE_BACKEND=firestore` と Firestore 権限/認証設定を確認してください。"
                f" (原因: {type(e).__name__}: {detail})"
            ) from e
        print(f"[gem] Firestore unavailable; falling back to memory store: {type(e).__name__} {e}")
        return InMemoryGemStore()
