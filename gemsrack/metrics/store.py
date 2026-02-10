from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


@dataclass(frozen=True)
class GemUsageRow:
    date: str  # YYYY-MM-DD
    gem_name: str
    count: int
    public_count: int
    ok_count: int
    error_count: int


@dataclass(frozen=True)
class GemUsageSummary:
    team_id: str
    days: int
    from_date: str  # YYYY-MM-DD
    to_date: str  # YYYY-MM-DD
    total_count: int
    public_count: int
    ok_count: int
    error_count: int
    by_day: list[dict]
    top_gems: list[dict]


class MetricsStore(ABC):
    @abstractmethod
    def record_gem_run(
        self,
        *,
        team_id: str,
        gem_name: str,
        user_id: str | None,
        public: bool,
        ok: bool,
        occurred_at: datetime | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_gem_usage_summary(self, *, team_id: str, days: int = 30, limit: int = 20) -> GemUsageSummary:
        raise NotImplementedError

    @abstractmethod
    def list_gem_usage_daily(self, *, team_id: str, days: int = 30) -> list[GemUsageRow]:
        raise NotImplementedError


class NoopMetricsStore(MetricsStore):
    def record_gem_run(  # noqa: D401
        self,
        *,
        team_id: str,
        gem_name: str,
        user_id: str | None,
        public: bool,
        ok: bool,
        occurred_at: datetime | None = None,
    ) -> None:
        return

    def get_gem_usage_summary(self, *, team_id: str, days: int = 30, limit: int = 20) -> GemUsageSummary:
        today = date.today()
        return GemUsageSummary(
            team_id=team_id,
            days=days,
            from_date=(today - timedelta(days=max(0, days - 1))).isoformat(),
            to_date=today.isoformat(),
            total_count=0,
            public_count=0,
            ok_count=0,
            error_count=0,
            by_day=[],
            top_gems=[],
        )

    def list_gem_usage_daily(self, *, team_id: str, days: int = 30) -> list[GemUsageRow]:
        return []


class InMemoryMetricsStore(MetricsStore):
    def __init__(self) -> None:
        # key: (team_id, YYYY-MM-DD, gem_name)
        self._gem_daily: dict[tuple[str, str, str], GemUsageRow] = {}
        # key: (team_id, YYYY-MM-DD)
        self._total_daily: dict[tuple[str, str], dict] = {}

    def record_gem_run(
        self,
        *,
        team_id: str,
        gem_name: str,
        user_id: str | None,  # unused for now
        public: bool,
        ok: bool,
        occurred_at: datetime | None = None,
    ) -> None:
        dt = occurred_at or datetime.now(timezone.utc)
        d = dt.date().isoformat()
        k = (team_id, d, gem_name)
        row = self._gem_daily.get(k) or GemUsageRow(
            date=d,
            gem_name=gem_name,
            count=0,
            public_count=0,
            ok_count=0,
            error_count=0,
        )
        row2 = GemUsageRow(
            date=row.date,
            gem_name=row.gem_name,
            count=row.count + 1,
            public_count=row.public_count + (1 if public else 0),
            ok_count=row.ok_count + (1 if ok else 0),
            error_count=row.error_count + (0 if ok else 1),
        )
        self._gem_daily[k] = row2

        kt = (team_id, d)
        tot = self._total_daily.get(kt) or {
            "date": d,
            "total_count": 0,
            "public_count": 0,
            "ok_count": 0,
            "error_count": 0,
        }
        tot["total_count"] += 1
        tot["public_count"] += 1 if public else 0
        tot["ok_count"] += 1 if ok else 0
        tot["error_count"] += 0 if ok else 1
        self._total_daily[kt] = tot

    def get_gem_usage_summary(self, *, team_id: str, days: int = 30, limit: int = 20) -> GemUsageSummary:
        days = max(1, min(days, 365))
        today = date.today()
        start = today - timedelta(days=days - 1)

        # totals by day
        by_day: list[dict] = []
        total_count = public_count = ok_count = error_count = 0
        for i in range(days):
            d = (start + timedelta(days=i)).isoformat()
            tot = self._total_daily.get((team_id, d)) or {
                "date": d,
                "total_count": 0,
                "public_count": 0,
                "ok_count": 0,
                "error_count": 0,
            }
            by_day.append(tot)
            total_count += int(tot["total_count"])
            public_count += int(tot["public_count"])
            ok_count += int(tot["ok_count"])
            error_count += int(tot["error_count"])

        # top gems
        agg: dict[str, dict] = {}
        for (tid, d, gem), row in self._gem_daily.items():
            if tid != team_id:
                continue
            if d < start.isoformat() or d > today.isoformat():
                continue
            a = agg.get(gem) or {"gem_name": gem, "count": 0, "public_count": 0, "ok_count": 0, "error_count": 0}
            a["count"] += row.count
            a["public_count"] += row.public_count
            a["ok_count"] += row.ok_count
            a["error_count"] += row.error_count
            agg[gem] = a
        top = sorted(agg.values(), key=lambda x: int(x["count"]), reverse=True)[: max(1, min(limit, 100))]

        return GemUsageSummary(
            team_id=team_id,
            days=days,
            from_date=start.isoformat(),
            to_date=today.isoformat(),
            total_count=total_count,
            public_count=public_count,
            ok_count=ok_count,
            error_count=error_count,
            by_day=by_day,
            top_gems=top,
        )

    def list_gem_usage_daily(self, *, team_id: str, days: int = 30) -> list[GemUsageRow]:
        days = max(1, min(days, 365))
        today = date.today()
        start = today - timedelta(days=days - 1)
        out: list[GemUsageRow] = []
        for (tid, d, gem), row in self._gem_daily.items():
            if tid != team_id:
                continue
            if d < start.isoformat() or d > today.isoformat():
                continue
            out.append(row)
        out.sort(key=lambda r: (r.date, r.gem_name))
        return out


class FirestoreMetricsStore(MetricsStore):
    def __init__(self, *, project_id: str | None = None) -> None:
        self._project_id = (
            project_id
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCP_PROJECT")
            or os.environ.get("GCLOUD_PROJECT")
        )
        from google.cloud import firestore  # type: ignore

        self._firestore = firestore
        if self._project_id:
            self._client = firestore.Client(project=self._project_id)
        else:
            self._client = firestore.Client()

    def _gem_daily_ref(self, *, team_id: str, d: str, gem_name: str):
        # workspaces/{team_id}/gem_usage_daily/{YYYY-MM-DD}__{gem_name}
        doc_id = f"{d}__{gem_name}"
        return (
            self._client.collection("workspaces")
            .document(team_id)
            .collection("gem_usage_daily")
            .document(doc_id)
        )

    def _total_daily_ref(self, *, team_id: str, d: str):
        # workspaces/{team_id}/gem_usage_totals_daily/{YYYY-MM-DD}
        return (
            self._client.collection("workspaces")
            .document(team_id)
            .collection("gem_usage_totals_daily")
            .document(d)
        )

    def record_gem_run(
        self,
        *,
        team_id: str,
        gem_name: str,
        user_id: str | None,
        public: bool,
        ok: bool,
        occurred_at: datetime | None = None,
    ) -> None:
        dt = occurred_at or datetime.now(timezone.utc)
        d = dt.date().isoformat()
        inc = self._firestore.Increment  # type: ignore[attr-defined]
        now = datetime.now(timezone.utc)

        # gem daily
        ref = self._gem_daily_ref(team_id=team_id, d=d, gem_name=gem_name)
        payload = {
            "date": d,
            "gem_name": gem_name,
            "updated_at": now,
            "count": inc(1),
            "public_count": inc(1 if public else 0),
            "ok_count": inc(1 if ok else 0),
            "error_count": inc(0 if ok else 1),
        }
        if user_id:
            # 直近の実行者のヒント程度（PIIではないが、必要なら削れます）
            payload["last_user_id"] = str(user_id)
        ref.set(payload, merge=True)

        # totals daily
        tref = self._total_daily_ref(team_id=team_id, d=d)
        tref.set(
            {
                "date": d,
                "updated_at": now,
                "total_count": inc(1),
                "public_count": inc(1 if public else 0),
                "ok_count": inc(1 if ok else 0),
                "error_count": inc(0 if ok else 1),
            },
            merge=True,
        )

    def get_gem_usage_summary(self, *, team_id: str, days: int = 30, limit: int = 20) -> GemUsageSummary:
        days = max(1, min(days, 365))
        limit = max(1, min(limit, 100))
        today = date.today()
        start = today - timedelta(days=days - 1)

        # totals by day (fast path)
        by_day: list[dict] = []
        total_count = public_count = ok_count = error_count = 0
        for i in range(days):
            d = (start + timedelta(days=i)).isoformat()
            snap = self._total_daily_ref(team_id=team_id, d=d).get()
            if snap.exists:
                tot = snap.to_dict() or {}
            else:
                tot = {}
            row = {
                "date": d,
                "total_count": int(tot.get("total_count") or 0),
                "public_count": int(tot.get("public_count") or 0),
                "ok_count": int(tot.get("ok_count") or 0),
                "error_count": int(tot.get("error_count") or 0),
            }
            by_day.append(row)
            total_count += row["total_count"]
            public_count += row["public_count"]
            ok_count += row["ok_count"]
            error_count += row["error_count"]

        # aggregate top gems across range (client-side)
        col = self._client.collection("workspaces").document(team_id).collection("gem_usage_daily")
        # doc_id is `{date}__{gem_name}` so we can range by prefix
        start_id = f"{start.isoformat()}__"
        end_id = f"{today.isoformat()}__\uf8ff"
        snaps = col.order_by("__name__").start_at({"__name__": start_id}).end_at({"__name__": end_id}).stream()

        agg: dict[str, dict] = {}
        for s in snaps:
            d = s.to_dict() or {}
            gem = str(d.get("gem_name") or "")
            if not gem:
                continue
            a = agg.get(gem) or {"gem_name": gem, "count": 0, "public_count": 0, "ok_count": 0, "error_count": 0}
            a["count"] += int(d.get("count") or 0)
            a["public_count"] += int(d.get("public_count") or 0)
            a["ok_count"] += int(d.get("ok_count") or 0)
            a["error_count"] += int(d.get("error_count") or 0)
            agg[gem] = a

        top = sorted(agg.values(), key=lambda x: int(x["count"]), reverse=True)[:limit]

        return GemUsageSummary(
            team_id=team_id,
            days=days,
            from_date=start.isoformat(),
            to_date=today.isoformat(),
            total_count=total_count,
            public_count=public_count,
            ok_count=ok_count,
            error_count=error_count,
            by_day=by_day,
            top_gems=top,
        )

    def list_gem_usage_daily(self, *, team_id: str, days: int = 30) -> list[GemUsageRow]:
        days = max(1, min(days, 365))
        today = date.today()
        start = today - timedelta(days=days - 1)

        col = self._client.collection("workspaces").document(team_id).collection("gem_usage_daily")
        start_id = f"{start.isoformat()}__"
        end_id = f"{today.isoformat()}__\uf8ff"
        snaps = col.order_by("__name__").start_at({"__name__": start_id}).end_at({"__name__": end_id}).stream()
        out: list[GemUsageRow] = []
        for s in snaps:
            d = s.to_dict() or {}
            gem = str(d.get("gem_name") or "")
            dtxt = str(d.get("date") or "")
            if not gem or not dtxt:
                continue
            out.append(
                GemUsageRow(
                    date=dtxt,
                    gem_name=gem,
                    count=int(d.get("count") or 0),
                    public_count=int(d.get("public_count") or 0),
                    ok_count=int(d.get("ok_count") or 0),
                    error_count=int(d.get("error_count") or 0),
                )
            )
        out.sort(key=lambda r: (r.date, r.gem_name))
        return out


def build_metrics_store() -> MetricsStore:
    """
    `GEM_METRICS_BACKEND` で計測先を選ぶ:
    - `firestore`: Firestore を必須化（失敗時は例外）
    - `memory`: インメモリ
    - `none`: 無効化（Noop）
    - `auto`(既定): Firestore を試し、失敗時はローカルのみ memory にフォールバック
    """
    backend = (os.environ.get("GEM_METRICS_BACKEND") or "auto").strip().lower()
    if backend in ("none", "noop", "off", "false"):
        return NoopMetricsStore()
    if backend == "memory":
        return InMemoryMetricsStore()
    if backend == "firestore":
        return FirestoreMetricsStore()

    if backend != "auto":
        raise RuntimeError("GEM_METRICS_BACKEND は `auto` / `firestore` / `memory` / `none` のいずれかにしてください")

    in_cloud_run = bool(os.environ.get("K_SERVICE"))
    try:
        return FirestoreMetricsStore()
    except Exception as e:
        if in_cloud_run:
            detail = (str(e) or type(e).__name__).strip().replace("\n", " ")
            detail = detail[:200]
            raise RuntimeError(
                "Cloud Run で Firestore（metrics）を初期化できません。"
                " `GEM_METRICS_BACKEND=firestore` と Firestore 権限/認証設定を確認してください。"
                f" (原因: {type(e).__name__}: {detail})"
            ) from e
        print(f"[metrics] Firestore unavailable; falling back to memory store: {type(e).__name__} {e}")
        return InMemoryMetricsStore()

