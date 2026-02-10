import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import type { GemDetail, GemSummary } from './api'
import { getGem, listGems } from './api'

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
    <div className="container">
      <div className="panel">
        <div className="panelBody">
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <div>
              <p className="title" style={{ marginBottom: 2 }}>
                Gemsrack
              </p>
              <p className="muted" style={{ margin: 0 }}>
                Gem 一覧（Slack外から閲覧）
              </p>
            </div>
            <div className="row">
              <button className="button secondary" onClick={() => refresh()} disabled={loading}>
                更新
              </button>
            </div>
          </div>

          <div style={{ height: 12 }} />

          <div className="row">
            <div className="field" style={{ minWidth: 260, flex: 1 }}>
              <div className="label">Team ID（任意 / 単一ワークスペースなら空でもOK）</div>
              <input
                className="input"
                value={teamIdInput}
                placeholder="例: T0123456789"
                onChange={(e) => setTeamIdInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') applyTeamId()
                }}
              />
            </div>
            <div style={{ height: 18 }} />
            <button className="button" onClick={applyTeamId} disabled={loading}>
              適用
            </button>

            <div className="field" style={{ minWidth: 260, flex: 1 }}>
              <div className="label">検索</div>
              <input
                className="input"
                value={query}
                placeholder="name / summary で絞り込み"
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>

          {error ? (
            <p style={{ marginTop: 12, marginBottom: 0, color: '#b91c1c' }}>{error}</p>
          ) : null}
        </div>
      </div>

      <div style={{ height: 16 }} />

      <div className="appShell">
        <div className="panel">
          <div className="panelHeader">
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <p className="title" style={{ marginBottom: 0 }}>
                Gem 一覧
              </p>
              <p className="muted" style={{ margin: 0 }}>
                {loading ? '読み込み中…' : `${filtered.length} 件`}
              </p>
            </div>
          </div>
          <div className="panelBody">
            {filtered.length === 0 ? (
              <p className="muted" style={{ margin: 0 }}>
                Gem がありません（または検索条件に一致しません）。
              </p>
            ) : (
              <div className="list">
                {filtered.map((g) => (
                  <div
                    key={g.name}
                    className={`card ${selectedName === g.name ? 'active' : ''}`}
                    onClick={() => setSelectedName(g.name)}
                  >
                    <div className="row" style={{ justifyContent: 'space-between' }}>
                      <div className="cardTitle">{g.name}</div>
                      <div className="muted" style={{ fontSize: 12 }}>
                        {g.updated_at ? new Date(g.updated_at).toLocaleString() : ''}
                      </div>
                    </div>
                    {g.summary ? <div className="muted">{g.summary}</div> : null}
                    <div className="pillRow">
                      {g.input_format ? <span className="pill">in: {g.input_format}</span> : null}
                      {g.output_format ? (
                        <span className="pill">out: {g.output_format}</span>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panelHeader">
            <p className="title" style={{ marginBottom: 0 }}>
              詳細
            </p>
          </div>
          <div className="panelBody">
            {!selectedName ? (
              <p className="muted" style={{ margin: 0 }}>
                左の一覧から Gem を選択してください。
              </p>
            ) : detailLoading ? (
              <p className="muted" style={{ margin: 0 }}>
                読み込み中…
              </p>
            ) : detailError ? (
              <p style={{ margin: 0, color: '#b91c1c' }}>{detailError}</p>
            ) : !selected ? (
              <p className="muted" style={{ margin: 0 }}>
                データがありません。
              </p>
            ) : (
              <div style={{ display: 'grid', gap: 10 }}>
                <div>
                  <div className="label">name</div>
                  <div style={{ fontWeight: 700 }}>{selected.name}</div>
                </div>
                {selected.summary ? (
                  <div>
                    <div className="label">summary</div>
                    <div>{selected.summary}</div>
                  </div>
                ) : null}
                {selected.system_prompt ? (
                  <div>
                    <div className="label">system_prompt</div>
                    <pre className="pre">{selected.system_prompt}</pre>
                  </div>
                ) : null}
                {selected.body ? (
                  <div>
                    <div className="label">body（互換: 静的テキスト）</div>
                    <pre className="pre">{selected.body}</pre>
                  </div>
                ) : null}
                <div className="row">
                  {selected.input_format ? <span className="pill">in: {selected.input_format}</span> : null}
                  {selected.output_format ? <span className="pill">out: {selected.output_format}</span> : null}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
