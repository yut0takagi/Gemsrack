import { useEffect, useMemo, useRef, useState } from 'react'
import { adminGetUsage, adminListGems, adminLogin, adminLogout, adminMe, adminSetGemEnabled } from './api'
import type { AdminListGemsResponse, AdminUsageResponse } from './api'

function formatInt(n: number) {
  return new Intl.NumberFormat().format(n)
}

function clampDays(n: number) {
  return Math.max(1, Math.min(365, n))
}

export function AdminPanel(props: { teamId?: string } = {}) {
  const { teamId } = props
  const [password, setPassword] = useState('')
  const [isAdmin, setIsAdmin] = useState(false)
  const [adminEnabled, setAdminEnabled] = useState(true)

  const [days, setDays] = useState(30)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [gems, setGems] = useState<AdminListGemsResponse['gems']>([])
  const [usage, setUsage] = useState<AdminUsageResponse | null>(null)

  const abortRef = useRef<AbortController | null>(null)

  async function doLogout() {
    try {
      await adminLogout()
    } catch {
      // ignore
    }
    setIsAdmin(false)
    setGems([])
    setUsage(null)
    setError(null)
  }

  async function refresh() {
    if (!isAdmin) {
      setError('Admin にログインしてください')
      return
    }
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
    // login状態の復元
    const ac = new AbortController()
    adminMe({ signal: ac.signal })
      .then((r) => {
        setAdminEnabled(Boolean(r.enabled))
        setIsAdmin(Boolean(r.admin))
      })
      .catch(() => {
        setAdminEnabled(false)
        setIsAdmin(false)
      })
    return () => ac.abort()
  }, [])

  useEffect(() => {
    if (!isAdmin) return
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, teamId, days])

  async function toggle(name: string, next: boolean) {
    if (!isAdmin) return
    const prev = gems
    setGems((xs) => xs.map((g) => (g.name === name ? { ...g, enabled: next } : g)))
    try {
      await adminSetGemEnabled({ name, enabled: next, teamId: teamId || undefined })
    } catch (e) {
      setGems(prev)
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const heatmap = useMemo(() => {
    const rows = usage?.by_gem_day ?? []
    const dates = Array.from(new Set(rows.map((r) => r.date))).sort()
    const gems2 = Array.from(new Set(rows.map((r) => r.gem_name))).sort()
    const m = new Map<string, number>()
    for (const r of rows) {
      m.set(`${r.gem_name}__${r.date}`, r.count)
    }
    return { dates, gems: gems2, map: m }
  }, [usage])

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md">
      <div className="flex flex-col gap-3 p-5 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-sm font-semibold tracking-wide text-slate-200">Admin</div>
          <div className="mt-1 text-xs text-slate-400">
            Gemの有効/無効（Slack実行可否）と詳細利用状況を管理します
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {!adminEnabled ? (
            <div className="text-sm text-slate-300">Adminは無効です（`ADMIN_PASSWORD`未設定）</div>
          ) : isAdmin ? (
            <>
              <button
                className="inline-flex h-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-semibold text-slate-100 hover:bg-white/10"
                onClick={doLogout}
              >
                ログアウト
              </button>
            </>
          ) : (
            <>
              <input
                className="h-10 w-72 rounded-xl border border-white/10 bg-black/30 px-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-fuchsia-300/50 focus:ring-2 focus:ring-fuchsia-300/20"
                placeholder="Admin Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    adminLogin({ password })
                      .then(() => {
                        setIsAdmin(true)
                        setPassword('')
                      })
                      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
                  }
                }}
              />
              <button
                className="inline-flex h-10 items-center justify-center rounded-xl bg-gradient-to-r from-fuchsia-400/90 via-indigo-400/90 to-cyan-400/90 px-4 text-sm font-semibold text-black hover:from-fuchsia-300 hover:via-indigo-300 hover:to-cyan-300 disabled:opacity-60"
                onClick={() => {
                  adminLogin({ password })
                    .then(() => {
                      setIsAdmin(true)
                      setPassword('')
                    })
                    .catch((e) => setError(e instanceof Error ? e.message : String(e)))
                }}
                disabled={!password.trim()}
              >
                ログイン
              </button>
            </>
          )}
          <button
            className="inline-flex h-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-semibold text-slate-100 hover:bg-white/10"
            onClick={doLogout}
          >
            リセット
          </button>
          <button
            className="inline-flex h-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-semibold text-slate-100 hover:bg-white/10 disabled:opacity-60"
            onClick={refresh}
            disabled={loading || !isAdmin}
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

        <div className="grid gap-5 lg:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-semibold text-slate-200">Gem 管理（Slack実行可否）</div>
              <div className="text-xs text-slate-500">{gems.length ? `${gems.length}件` : ''}</div>
            </div>

            {gems.length === 0 ? (
              <div className="text-sm text-slate-400">トークン適用後に表示されます。</div>
            ) : (
              <div className="grid gap-2">
                {gems.map((g) => (
                  <div
                    key={g.name}
                    className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-black/30 px-4 py-3"
                  >
                    <div className="min-w-0">
                      <div className="truncate font-mono text-sm font-semibold text-slate-100">{g.name}</div>
                      <div className="mt-1 line-clamp-2 text-xs text-slate-300">{g.summary || '（summaryなし）'}</div>
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
                    </div>
                    <button
                      className={[
                        'shrink-0 rounded-xl px-3 py-2 text-sm font-semibold transition',
                        g.enabled
                          ? 'bg-emerald-400/90 text-black hover:bg-emerald-300'
                          : 'bg-white/10 text-slate-200 hover:bg-white/15',
                      ].join(' ')}
                      onClick={() => toggle(g.name, !g.enabled)}
                      title={g.enabled ? 'Slack実行: ON' : 'Slack実行: OFF'}
                    >
                      {g.enabled ? 'ON' : 'OFF'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-slate-200">詳細利用状況</div>
                <div className="mt-1 text-xs text-slate-500">
                  期間合計: {usage ? formatInt(usage.summary.total_count) : '—'} / 失敗:{' '}
                  {usage ? formatInt(usage.summary.error_count) : '—'}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div className="text-xs text-slate-400">days</div>
                <select
                  className="h-10 rounded-xl border border-white/10 bg-black/30 px-3 text-sm text-slate-100 outline-none"
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                >
                  <option value={7}>7</option>
                  <option value={30}>30</option>
                  <option value={90}>90</option>
                </select>
              </div>
            </div>

            {!usage ? (
              <div className="text-sm text-slate-400">トークン適用後に表示されます。</div>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-black/30 p-3">
                {heatmap.dates.length === 0 || heatmap.gems.length === 0 ? (
                  <div className="text-sm text-slate-400">まだデータがありません。</div>
                ) : (
                  <table className="w-full text-left text-xs">
                    <thead className="text-[11px] text-slate-400">
                      <tr className="border-b border-white/10">
                        <th className="py-2 pr-3 font-medium">Gem</th>
                        {heatmap.dates.slice(-7).map((d) => (
                          <th key={d} className="py-2 pr-2 font-medium">
                            {d.slice(5)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {heatmap.gems.map((g) => (
                        <tr key={g} className="border-b border-white/5">
                          <td className="py-2 pr-3 font-mono text-slate-100">{g}</td>
                          {heatmap.dates.slice(-7).map((d) => {
                            const v = heatmap.map.get(`${g}__${d}`) ?? 0
                            return (
                              <td key={d} className="py-2 pr-2 text-slate-200">
                                {v ? formatInt(v) : <span className="text-slate-600">0</span>}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

