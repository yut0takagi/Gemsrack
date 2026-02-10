import { useEffect, useMemo, useRef, useState } from 'react'
import { adminGetUsage, adminListGems, adminSetGemEnabled } from './api'
import type { AdminListGemsResponse, AdminUsageResponse } from './api'

function formatInt(n: number) {
  return new Intl.NumberFormat().format(n)
}

function clampDays(n: number) {
  return Math.max(1, Math.min(365, n))
}

function pct(n: number, d: number) {
  if (!d) return '—'
  return `${Math.round((n / d) * 100)}%`
}

export function AdminPanel(props: { teamId?: string } = {}) {
  const { teamId } = props

  const [days, setDays] = useState(30)
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<'all' | 'enabled' | 'disabled'>('all')
  const [sort, setSort] = useState<'runs_desc' | 'name_asc' | 'errors_desc'>('runs_desc')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [gems, setGems] = useState<AdminListGemsResponse['gems']>([])
  const [usage, setUsage] = useState<AdminUsageResponse | null>(null)

  const abortRef = useRef<AbortController | null>(null)

  async function refresh() {
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac

    setLoading(true)
    setError(null)
    try {
      const [g, u] = await Promise.all([
        adminListGems({ teamId: teamId || undefined, signal: ac.signal }),
        adminGetUsage({ teamId: teamId || undefined, days: clampDays(days), signal: ac.signal }),
      ])
      setGems(g.gems)
      setUsage(u)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teamId, days])

  async function toggle(name: string, next: boolean) {
    const prev = gems
    setGems((xs) => xs.map((g) => (g.name === name ? { ...g, enabled: next } : g)))
    try {
      await adminSetGemEnabled({ name, enabled: next, teamId: teamId || undefined })
    } catch (e) {
      setGems(prev)
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const byDay = useMemo(() => usage?.summary.by_day ?? [], [usage])

  const last7Dates = useMemo(() => byDay.map((d) => d.date).slice(-7), [byDay])

  const usageAgg = useMemo(() => {
    const rows = usage?.by_gem_day ?? []
    const map = new Map<
      string,
      { count: number; public: number; ok: number; err: number; byDay: Map<string, number> }
    >()
    for (const r of rows) {
      const cur =
        map.get(r.gem_name) ?? ({ count: 0, public: 0, ok: 0, err: 0, byDay: new Map<string, number>() } as const)
      const next = {
        count: cur.count + r.count,
        public: cur.public + r.public_count,
        ok: cur.ok + r.ok_count,
        err: cur.err + r.error_count,
        byDay: new Map(cur.byDay),
      }
      next.byDay.set(r.date, r.count)
      map.set(r.gem_name, next)
    }
    return map
  }, [usage])

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    let out = gems.map((g) => {
      const u = usageAgg.get(g.name)
      return {
        ...g,
        runs: u?.count ?? 0,
        pub: u?.public ?? 0,
        ok: u?.ok ?? 0,
        err: u?.err ?? 0,
      }
    })

    if (filter !== 'all') out = out.filter((g) => (filter === 'enabled' ? g.enabled : !g.enabled))
    if (q) out = out.filter((g) => (g.name + ' ' + (g.summary || '')).toLowerCase().includes(q))

    if (sort === 'name_asc') out.sort((a, b) => a.name.localeCompare(b.name))
    else if (sort === 'errors_desc') out.sort((a, b) => b.err - a.err || b.runs - a.runs || a.name.localeCompare(b.name))
    else out.sort((a, b) => b.runs - a.runs || a.name.localeCompare(b.name))

    return out
  }, [gems, usageAgg, filter, query, sort])

  const summary = usage?.summary
  const total = summary?.total_count ?? 0
  const ok = summary?.ok_count ?? 0
  const pub = summary?.public_count ?? 0
  const err = summary?.error_count ?? 0

  function Spark(props: { gemName: string }) {
    const u = usageAgg.get(props.gemName)
    const values = last7Dates.map((d) => u?.byDay.get(d) ?? 0)
    const max = Math.max(1, ...values)
    return (
      <div className="flex h-7 items-end gap-1">
        {values.map((v, i) => (
          // eslint-disable-next-line react/no-array-index-key
          <div
            key={i}
            className="w-2 rounded-sm bg-gradient-to-t from-cyan-400/60 via-indigo-400/60 to-fuchsia-400/60"
            style={{ height: `${Math.max(2, Math.round((v / max) * 28))}px` }}
            title={`${v}`}
          />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {error ? (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
          {error}
          <div className="mt-2 text-xs text-red-200/80">
            401 の場合は <a className="underline" href="/admin/login">/admin/login</a> からログインしてください。
          </div>
        </div>
      ) : null}

      <section className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md">
        <div className="flex flex-col gap-3 p-5 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-sm font-semibold tracking-wide text-slate-200">Overview</div>
            <div className="mt-1 text-xs text-slate-400">実行回数と健全性（期間: {days}日）</div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              className="h-10 rounded-xl border border-white/10 bg-black/30 px-3 text-sm text-slate-100 outline-none"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            >
              <option value={7}>7日</option>
              <option value={30}>30日</option>
              <option value={90}>90日</option>
            </select>
            <button
              className="inline-flex h-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-semibold text-slate-100 hover:bg-white/10 disabled:opacity-60"
              onClick={refresh}
              disabled={loading}
            >
              更新
            </button>
          </div>
        </div>
        <div className="border-t border-white/10 p-5">
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
              <div className="text-xs text-slate-400">実行</div>
              <div className="mt-2 text-2xl font-semibold text-slate-100">{formatInt(total)}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
              <div className="text-xs text-slate-400">成功率</div>
              <div className="mt-2 text-2xl font-semibold text-slate-100">{pct(ok, total)}</div>
              <div className="mt-1 text-xs text-slate-400">
                成功 {formatInt(ok)} / 失敗 {formatInt(err)}
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
              <div className="text-xs text-slate-400">公開率</div>
              <div className="mt-2 text-2xl font-semibold text-slate-100">{pct(pub, total)}</div>
              <div className="mt-1 text-xs text-slate-400">公開 {formatInt(pub)}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
              <div className="text-xs text-slate-400">Gem数</div>
              <div className="mt-2 text-2xl font-semibold text-slate-100">{formatInt(gems.length)}</div>
              <div className="mt-1 text-xs text-slate-400">
                ON {formatInt(gems.filter((g) => g.enabled).length)} / OFF {formatInt(gems.filter((g) => !g.enabled).length)}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md">
        <div className="p-5">
          <div className="text-sm font-semibold tracking-wide text-slate-200">Trend</div>
          <div className="mt-1 text-xs text-slate-400">日別の実行回数（直近）</div>
        </div>
        <div className="border-t border-white/10 p-5">
          {byDay.length === 0 ? (
            <div className="text-sm text-slate-400">まだデータがありません。</div>
          ) : (
            <div className="grid gap-2">
              {byDay.slice(-14).map((d) => {
                const max = Math.max(1, ...byDay.slice(-14).map((x) => x.total_count))
                const w = Math.round((d.total_count / max) * 100)
                return (
                  <div key={d.date} className="grid grid-cols-[90px_1fr_60px] items-center gap-3">
                    <div className="font-mono text-xs text-slate-400">{d.date}</div>
                    <div className="h-2 rounded-full bg-white/10">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-cyan-400/70 via-indigo-400/70 to-fuchsia-400/70"
                        style={{ width: `${w}%` }}
                      />
                    </div>
                    <div className="text-right text-xs text-slate-300">{formatInt(d.total_count)}</div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md">
        <div className="flex flex-col gap-3 p-5 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="text-sm font-semibold tracking-wide text-slate-200">Gems</div>
            <div className="mt-1 text-xs text-slate-400">Slackコマンド可否（ON/OFF）と利用状況</div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              className="h-10 w-64 rounded-xl border border-white/10 bg-black/30 px-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-indigo-300/50 focus:ring-2 focus:ring-indigo-300/20"
              placeholder="検索（name / summary）"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <select
              className="h-10 rounded-xl border border-white/10 bg-black/30 px-3 text-sm text-slate-100 outline-none"
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
            >
              <option value="all">すべて</option>
              <option value="enabled">ONのみ</option>
              <option value="disabled">OFFのみ</option>
            </select>
            <select
              className="h-10 rounded-xl border border-white/10 bg-black/30 px-3 text-sm text-slate-100 outline-none"
              value={sort}
              onChange={(e) => setSort(e.target.value as any)}
            >
              <option value="runs_desc">実行数（多い順）</option>
              <option value="errors_desc">失敗（多い順）</option>
              <option value="name_asc">名前（A→Z）</option>
            </select>
          </div>
        </div>

        <div className="border-t border-white/10 p-3">
          {rows.length === 0 ? (
            <div className="p-3 text-sm text-slate-400">該当するGemがありません。</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-slate-400">
                  <tr className="border-b border-white/10">
                    <th className="py-2 px-3 font-medium">Slack</th>
                    <th className="py-2 px-3 font-medium">Gem</th>
                    <th className="py-2 px-3 font-medium">期間実行</th>
                    <th className="py-2 px-3 font-medium">成功率</th>
                    <th className="py-2 px-3 font-medium">公開率</th>
                    <th className="py-2 px-3 font-medium">直近7日</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((g) => (
                    <tr key={g.name} className="border-b border-white/5 align-top">
                      <td className="py-3 px-3">
                        <button
                          className={[
                            'rounded-xl px-3 py-2 text-sm font-semibold transition',
                            g.enabled
                              ? 'bg-emerald-400/90 text-black hover:bg-emerald-300'
                              : 'bg-white/10 text-slate-200 hover:bg-white/15',
                          ].join(' ')}
                          onClick={() => toggle(g.name, !g.enabled)}
                          title={g.enabled ? 'Slack実行: ON' : 'Slack実行: OFF'}
                        >
                          {g.enabled ? 'ON' : 'OFF'}
                        </button>
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-mono font-semibold text-slate-100">{g.name}</div>
                        <div className="mt-1 max-w-xl text-xs text-slate-300">{g.summary || '（summaryなし）'}</div>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-400">
                          {g.input_format ? (
                            <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5">
                              in: {g.input_format}
                            </span>
                          ) : null}
                          {g.output_format ? (
                            <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5">
                              out: {g.output_format}
                            </span>
                          ) : null}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-200">{formatInt(g.runs)}</td>
                      <td className="py-3 px-3 text-slate-200">{pct(g.ok, g.runs)}</td>
                      <td className="py-3 px-3 text-slate-200">{pct(g.pub, g.runs)}</td>
                      <td className="py-3 px-3">
                        <Spark gemName={g.name} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

