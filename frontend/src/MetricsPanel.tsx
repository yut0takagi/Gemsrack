import { useEffect, useMemo, useRef, useState } from 'react'
import type { GemUsageResponse, GemUsageTopGemRow } from './api'
import { getGemUsage } from './api'

function pct(n: number, d: number) {
  if (!d) return '—'
  return `${Math.round((n / d) * 100)}%`
}

function formatInt(n: number) {
  return new Intl.NumberFormat().format(n)
}

function SparkBars(props: { values: number[] }) {
  const { values } = props
  const max = Math.max(1, ...values)
  return (
    <div className="flex h-10 items-end gap-1">
      {values.map((v, i) => (
        <div
          // eslint-disable-next-line react/no-array-index-key
          key={i}
          className="w-2 rounded-sm bg-gradient-to-t from-cyan-400/60 via-indigo-400/60 to-fuchsia-400/60"
          style={{ height: `${Math.max(2, Math.round((v / max) * 40))}px` }}
          title={`${v}`}
        />
      ))}
    </div>
  )
}

function TopGemsTable(props: { rows: GemUsageTopGemRow[] }) {
  const { rows } = props
  if (rows.length === 0) {
    return <div className="text-sm text-slate-400">まだデータがありません。</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs text-slate-400">
          <tr className="border-b border-white/10">
            <th className="py-2 pr-3 font-medium">Gem</th>
            <th className="py-2 pr-3 font-medium">実行</th>
            <th className="py-2 pr-3 font-medium">公開率</th>
            <th className="py-2 pr-3 font-medium">成功率</th>
            <th className="py-2 pr-3 font-medium">失敗</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.gem_name} className="border-b border-white/5">
              <td className="py-2 pr-3 font-mono text-slate-100">{r.gem_name}</td>
              <td className="py-2 pr-3 text-slate-200">{formatInt(r.count)}</td>
              <td className="py-2 pr-3 text-slate-200">{pct(r.public_count, r.count)}</td>
              <td className="py-2 pr-3 text-slate-200">{pct(r.ok_count, r.count)}</td>
              <td className="py-2 pr-3 text-slate-300">{formatInt(r.error_count)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function MetricsPanel(props: { teamId?: string }) {
  const { teamId } = props
  const [days, setDays] = useState<number>(30)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<GemUsageResponse | null>(null)

  const abortRef = useRef<AbortController | null>(null)

  async function refresh() {
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac

    setLoading(true)
    setError(null)
    try {
      const res = await getGemUsage({ teamId: teamId || undefined, days, limit: 20, signal: ac.signal })
      setData(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teamId, days])

  const spark = useMemo(() => {
    const values = (data?.by_day ?? []).map((r) => r.total_count)
    const last7 = values.slice(-7)
    return last7.length > 0 ? last7 : values
  }, [data])

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md">
      <div className="flex flex-col gap-3 p-5 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-sm font-semibold tracking-wide text-slate-200">KPI（Gem 利用状況）</div>
          <div className="mt-1 text-xs text-slate-400">
            Slack経由の実行を日次で集計（表示: <span className="font-mono">/api/metrics/gem-usage</span>）
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs text-slate-300">期間</label>
          <select
            className="h-10 rounded-xl border border-white/10 bg-black/30 px-3 text-sm text-slate-100 outline-none focus:border-indigo-300/50 focus:ring-2 focus:ring-indigo-300/20"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>7日</option>
            <option value={30}>30日</option>
            <option value={90}>90日</option>
          </select>

          <button
            className="inline-flex h-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-semibold text-slate-100 hover:bg-white/10 disabled:opacity-60"
            onClick={() => refresh()}
            disabled={loading}
          >
            更新
          </button>
        </div>
      </div>

      <div className="border-t border-white/10 p-5">
        {error ? (
          <div className="mb-4 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
            <div className="text-xs text-slate-400">期間</div>
            <div className="mt-1 text-sm text-slate-200">
              {data ? (
                <span className="font-mono">
                  {data.from_date} → {data.to_date}
                </span>
              ) : (
                <span className="text-slate-500">—</span>
              )}
            </div>
            <div className="mt-3">{spark.length ? <SparkBars values={spark} /> : <div className="h-10" />}</div>
            <div className="mt-2 text-[11px] text-slate-500">直近の推移（簡易）</div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
            <div className="text-xs text-slate-400">実行回数（合計）</div>
            <div className="mt-2 text-2xl font-semibold text-slate-100">
              {data ? formatInt(data.total_count) : '—'}
            </div>
            <div className="mt-2 text-sm text-slate-300">
              公開: {data ? formatInt(data.public_count) : '—'}（{data ? pct(data.public_count, data.total_count) : '—'}）
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
            <div className="text-xs text-slate-400">成功率</div>
            <div className="mt-2 text-2xl font-semibold text-slate-100">
              {data ? pct(data.ok_count, data.total_count) : '—'}
            </div>
            <div className="mt-2 text-sm text-slate-300">
              成功: {data ? formatInt(data.ok_count) : '—'} / 失敗: {data ? formatInt(data.error_count) : '—'}
            </div>
          </div>
        </div>

        <div className="mt-6">
          <div className="mb-2 text-sm font-semibold text-slate-200">Top Gems</div>
          <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
            {loading && !data ? <div className="text-sm text-slate-400">読み込み中…</div> : null}
            <TopGemsTable rows={data?.top_gems ?? []} />
          </div>
        </div>
      </div>
    </section>
  )
}

