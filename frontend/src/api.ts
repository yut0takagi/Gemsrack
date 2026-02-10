export type GemSummary = {
  team_id: string
  name: string
  summary: string
  input_format: string
  output_format: string
  created_by: string | null
  created_at: string
  updated_at: string
}

export type ListGemsResponse = {
  team_id: string
  count: number
  gems: GemSummary[]
}

export type GemDetail = GemSummary & {
  body: string
  system_prompt: string
}

export type GetGemResponse = {
  team_id: string
  gem: GemDetail
}

function buildQuery(params: Record<string, string | number | undefined | null>) {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null) continue
    const s = String(v).trim()
    if (!s) continue
    q.set(k, s)
  }
  const out = q.toString()
  return out ? `?${out}` : ''
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`API error (${res.status}): ${text || res.statusText}`)
  }
  return (await res.json()) as T
}

export async function listGems(opts: {
  teamId?: string
  limit?: number
  signal?: AbortSignal
}): Promise<ListGemsResponse> {
  const query = buildQuery({ team_id: opts.teamId, limit: opts.limit ?? 200 })
  return await fetchJson<ListGemsResponse>(`/api/gems${query}`, { signal: opts.signal })
}

export async function getGem(opts: {
  name: string
  teamId?: string
  signal?: AbortSignal
}): Promise<GetGemResponse> {
  const query = buildQuery({ team_id: opts.teamId })
  return await fetchJson<GetGemResponse>(`/api/gems/${encodeURIComponent(opts.name)}${query}`, {
    signal: opts.signal,
  })
}

