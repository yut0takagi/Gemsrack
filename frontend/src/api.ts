export type GemSummary = {
  team_id: string
  name: string
  summary: string
  input_format: string
  output_format: string
  enabled?: boolean
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

export type GemUsageByDayRow = {
  date: string
  total_count: number
  public_count: number
  ok_count: number
  error_count: number
}

export type GemUsageTopGemRow = {
  gem_name: string
  count: number
  public_count: number
  ok_count: number
  error_count: number
}

export type GemUsageResponse = {
  team_id: string
  days: number
  from_date: string
  to_date: string
  total_count: number
  public_count: number
  ok_count: number
  error_count: number
  by_day: GemUsageByDayRow[]
  top_gems: GemUsageTopGemRow[]
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

type FetchInit = Parameters<typeof fetch>[1]

async function fetchJson<T>(path: string, init?: FetchInit): Promise<T> {
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

export async function getGemUsage(opts: {
  teamId?: string
  days?: number
  limit?: number
  signal?: AbortSignal
}): Promise<GemUsageResponse> {
  const query = buildQuery({
    team_id: opts.teamId,
    days: opts.days ?? 30,
    limit: opts.limit ?? 20,
  })
  return await fetchJson<GemUsageResponse>(`/api/metrics/gem-usage${query}`, { signal: opts.signal })
}

export type AdminListGemsResponse = {
  team_id: string
  count: number
  gems: Array<{
    name: string
    summary: string
    enabled: boolean
    input_format: string
    output_format: string
    updated_at: string
  }>
}

export type AdminUsageResponse = {
  team_id: string
  days: number
  summary: GemUsageResponse
  by_gem_day: Array<{
    date: string
    gem_name: string
    count: number
    public_count: number
    ok_count: number
    error_count: number
  }>
}

export async function adminMe(opts?: { signal?: AbortSignal }): Promise<{ admin: boolean; enabled: boolean }> {
  return await fetchJson<{ admin: boolean; enabled: boolean }>(`/api/admin/me`, { signal: opts?.signal })
}

export async function adminLogin(opts: { password: string; signal?: AbortSignal }): Promise<{ ok: boolean }> {
  return await fetchJson<{ ok: boolean }>(`/api/admin/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: opts.password }),
    signal: opts.signal,
  })
}

export async function adminLogout(opts?: { signal?: AbortSignal }): Promise<{ ok: boolean }> {
  return await fetchJson<{ ok: boolean }>(`/api/admin/logout`, { method: 'POST', signal: opts?.signal })
}

export async function adminListGems(opts: {
  teamId?: string
  signal?: AbortSignal
}): Promise<AdminListGemsResponse> {
  const query = buildQuery({ team_id: opts.teamId })
  return await fetchJson<AdminListGemsResponse>(`/api/admin/gems${query}`, { signal: opts.signal })
}

export async function adminSetGemEnabled(opts: {
  name: string
  enabled: boolean
  teamId?: string
  signal?: AbortSignal
}): Promise<{ team_id: string; gem: { name: string; enabled: boolean } }> {
  const query = buildQuery({ team_id: opts.teamId })
  return await fetchJson<{ team_id: string; gem: { name: string; enabled: boolean } }>(
    `/api/admin/gems/${encodeURIComponent(opts.name)}${query}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: opts.enabled }),
      signal: opts.signal,
    },
  )
}

export async function adminGetUsage(opts: {
  teamId?: string
  days?: number
  signal?: AbortSignal
}): Promise<AdminUsageResponse> {
  const query = buildQuery({ team_id: opts.teamId, days: opts.days ?? 30 })
  return await fetchJson<AdminUsageResponse>(`/api/admin/usage${query}`, { signal: opts.signal })
}

