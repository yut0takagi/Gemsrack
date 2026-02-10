import { useEffect, useMemo, useRef, useState } from 'react'
import type { GemDetail, GemSummary } from './api'
import { getGem, listGems } from './api'
import { VantaHaloBackground } from './VantaHaloBackground'

function App() {
  const TEAM_ID_KEY = 'gemsrack_team_id'

  const [teamIdInput, setTeamIdInput] = useState<string>(() => {
    return localStorage.getItem(TEAM_ID_KEY) ?? ''
  })
  const [teamId, setTeamId] = useState<string>(() => {
    return localStorage.getItem(TEAM_ID_KEY) ?? ''
  })
  const [query, setQuery] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [gems, setGems] = useState<GemSummary[]>([])

  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [selected, setSelected] = useState<GemDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)

  const listAbortRef = useRef<AbortController | null>(null)
  const detailAbortRef = useRef<AbortController | null>(null)

  async function refresh() {
    listAbortRef.current?.abort()
    const ac = new AbortController()
    listAbortRef.current = ac

    setLoading(true)
    setError(null)
    try {
      const res = await listGems({ teamId: teamId || undefined, limit: 200, signal: ac.signal })
      setGems(res.gems)
      // 選択中が消えていたらクリア
      if (selectedName && !res.gems.some((g) => g.name === selectedName)) {
        setSelectedName(null)
        setSelected(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teamId])

  useEffect(() => {
    if (!selectedName) return
    detailAbortRef.current?.abort()
    const ac = new AbortController()
    detailAbortRef.current = ac

    setDetailLoading(true)
    setDetailError(null)
    setSelected(null)
    getGem({ name: selectedName, teamId: teamId || undefined, signal: ac.signal })
      .then((r) => setSelected(r.gem))
      .catch((e) => setDetailError(e instanceof Error ? e.message : String(e)))
      .finally(() => setDetailLoading(false))
  }, [selectedName, teamId])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return gems
    return gems.filter((g) => (g.name + ' ' + (g.summary || '')).toLowerCase().includes(q))
  }, [gems, query])

  function applyTeamId() {
    const next = teamIdInput.trim()
    localStorage.setItem(TEAM_ID_KEY, next)
    setTeamId(next)
  }

  return (
    <div className="relative min-h-screen text-slate-100">
      <VantaHaloBackground />

      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md">
          <div className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
              <div className="text-lg font-semibold tracking-wide">
                <span className="bg-gradient-to-r from-cyan-300 via-indigo-300 to-fuchsia-300 bg-clip-text text-transparent">
                  Gemsrack
                </span>
              </div>
              <div className="text-sm text-slate-300">Gem 一覧（Slack外から閲覧）</div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
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
            <div className="grid gap-3 md:grid-cols-[1fr_auto_1fr] md:items-end">
              <label className="space-y-1">
                <div className="text-xs font-medium text-slate-300">Team ID（任意 / 単一WSなら空でもOK）</div>
                <input
                  className="h-10 w-full rounded-xl border border-white/10 bg-black/30 px-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-300/20"
                  value={teamIdInput}
                  placeholder="例: T0123456789"
                  onChange={(e) => setTeamIdInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') applyTeamId()
                  }}
                />
              </label>

              <button
                className="inline-flex h-10 items-center justify-center rounded-xl bg-gradient-to-r from-cyan-400/90 via-indigo-400/90 to-fuchsia-400/90 px-4 text-sm font-semibold text-black hover:from-cyan-300 hover:via-indigo-300 hover:to-fuchsia-300 disabled:opacity-60"
                onClick={applyTeamId}
                disabled={loading}
              >
                適用
              </button>

              <label className="space-y-1">
                <div className="text-xs font-medium text-slate-300">検索</div>
                <input
                  className="h-10 w-full rounded-xl border border-white/10 bg-black/30 px-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-indigo-300/50 focus:ring-2 focus:ring-indigo-300/20"
                  value={query}
                  placeholder="name / summary で絞り込み"
                  onChange={(e) => setQuery(e.target.value)}
                />
              </label>
            </div>

            {error ? (
              <div className="mt-3 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
                {error}
              </div>
            ) : null}
          </div>
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <section className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md">
            <div className="flex items-center justify-between p-5">
              <div className="text-sm font-semibold tracking-wide text-slate-200">Gem 一覧</div>
              <div className="text-xs text-slate-400">{loading ? '読み込み中…' : `${filtered.length} 件`}</div>
            </div>
            <div className="border-t border-white/10 p-3">
              {filtered.length === 0 ? (
                <div className="p-3 text-sm text-slate-400">
                  Gem がありません（または検索条件に一致しません）。
                </div>
              ) : (
                <div className="grid gap-2">
                  {filtered.map((g) => {
                    const active = selectedName === g.name
                    return (
                      <button
                        key={g.name}
                        onClick={() => setSelectedName(g.name)}
                        className={[
                          'group w-full rounded-2xl border px-4 py-3 text-left transition',
                          active
                            ? 'border-cyan-300/30 bg-cyan-300/10'
                            : 'border-white/10 bg-black/25 hover:border-white/20 hover:bg-black/35',
                        ].join(' ')}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="truncate font-mono text-sm font-semibold text-slate-100">
                              {g.name}
                            </div>
                            {g.summary ? (
                              <div className="mt-1 line-clamp-2 text-xs text-slate-300">
                                {g.summary}
                              </div>
                            ) : (
                              <div className="mt-1 text-xs text-slate-500">（summaryなし）</div>
                            )}
                          </div>
                          <div className="shrink-0 text-[11px] text-slate-500">
                            {g.updated_at ? new Date(g.updated_at).toLocaleString() : ''}
                          </div>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {g.input_format ? (
                            <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-slate-200">
                              in: {g.input_format}
                            </span>
                          ) : null}
                          {g.output_format ? (
                            <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-slate-200">
                              out: {g.output_format}
                            </span>
                          ) : null}
                        </div>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          </section>

          <aside className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md">
            <div className="p-5">
              <div className="text-sm font-semibold tracking-wide text-slate-200">詳細</div>
              <div className="mt-3">
                {!selectedName ? (
                  <div className="text-sm text-slate-400">左の一覧から Gem を選択してください。</div>
                ) : detailLoading ? (
                  <div className="text-sm text-slate-400">読み込み中…</div>
                ) : detailError ? (
                  <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
                    {detailError}
                  </div>
                ) : !selected ? (
                  <div className="text-sm text-slate-400">データがありません。</div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <div className="text-xs font-medium text-slate-400">name</div>
                      <div className="mt-1 font-mono text-sm font-semibold">{selected.name}</div>
                    </div>

                    {selected.summary ? (
                      <div>
                        <div className="text-xs font-medium text-slate-400">summary</div>
                        <div className="mt-1 text-sm text-slate-200">{selected.summary}</div>
                      </div>
                    ) : null}

                    {selected.system_prompt ? (
                      <div>
                        <div className="text-xs font-medium text-slate-400">system_prompt</div>
                        <pre className="mt-2 max-h-64 overflow-auto rounded-2xl border border-white/10 bg-black/40 p-3 text-xs leading-relaxed text-slate-200">
                          {selected.system_prompt}
                        </pre>
                      </div>
                    ) : null}

                    {selected.body ? (
                      <div>
                        <div className="text-xs font-medium text-slate-400">body（互換: 静的テキスト）</div>
                        <pre className="mt-2 max-h-64 overflow-auto rounded-2xl border border-white/10 bg-black/40 p-3 text-xs leading-relaxed text-slate-200">
                          {selected.body}
                        </pre>
                      </div>
                    ) : null}

                    <div className="flex flex-wrap gap-2">
                      {selected.input_format ? (
                        <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-slate-200">
                          in: {selected.input_format}
                        </span>
                      ) : null}
                      {selected.output_format ? (
                        <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-slate-200">
                          out: {selected.output_format}
                        </span>
                      ) : null}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </aside>
        </div>

        <footer className="mt-8 text-center text-xs text-slate-500">
          <span className="font-mono">/api/gems</span> から取得しています
        </footer>
      </div>
    </div>
  )
}

export default App
