import { useEffect, useState } from 'react'
import { adminLogin, adminMe } from './api'
import { VantaHaloBackground } from './VantaHaloBackground'

export function AdminLoginApp() {
  const [adminEnabled, setAdminEnabled] = useState(true)
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const ac = new AbortController()
    adminMe({ signal: ac.signal })
      .then((r) => {
        setAdminEnabled(Boolean(r.enabled))
        if (r.admin) {
          window.location.href = '/admin/dashboard'
        }
      })
      .catch(() => setAdminEnabled(false))
    return () => ac.abort()
  }, [])

  async function submit() {
    setLoading(true)
    setError(null)
    try {
      await adminLogin({ password: password.trim() })
      window.location.href = '/admin/dashboard'
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen text-slate-100">
      <VantaHaloBackground />

      <div className="mx-auto max-w-md px-4 py-10">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <div className="text-lg font-semibold tracking-wide">
            <span className="bg-gradient-to-r from-fuchsia-300 via-indigo-300 to-cyan-300 bg-clip-text text-transparent">
              Gemsrack Admin
            </span>
          </div>
          <div className="mt-1 text-sm text-slate-300">ログイン</div>

          {!adminEnabled ? (
            <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-200">
              Admin は無効です（`ADMIN_PASSWORD` / `SECRET_KEY` が未設定）
            </div>
          ) : null}

          {error ? (
            <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
              {error}
            </div>
          ) : null}

          <label className="mt-5 block space-y-2">
            <div className="text-xs font-medium text-slate-300">Password</div>
            <input
              className="h-11 w-full rounded-xl border border-white/10 bg-black/30 px-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-fuchsia-300/50 focus:ring-2 focus:ring-fuchsia-300/20"
              placeholder="Admin Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void submit()
              }}
              type="password"
              autoComplete="current-password"
              disabled={!adminEnabled || loading}
            />
          </label>

          <button
            className="mt-4 inline-flex h-11 w-full items-center justify-center rounded-xl bg-gradient-to-r from-fuchsia-400/90 via-indigo-400/90 to-cyan-400/90 px-4 text-sm font-semibold text-black hover:from-fuchsia-300 hover:via-indigo-300 hover:to-cyan-300 disabled:opacity-60"
            onClick={() => void submit()}
            disabled={!adminEnabled || loading || !password.trim()}
          >
            {loading ? 'ログイン中…' : 'ログイン'}
          </button>

          <a
            href="/"
            className="mt-4 inline-flex h-10 w-full items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-semibold text-slate-100 hover:bg-white/10"
          >
            公開ページへ戻る
          </a>
        </div>

        <div className="mt-4 text-center text-xs text-slate-500">
          <span className="font-mono">/api/admin/login</span>（セッション認証）
        </div>
      </div>
    </div>
  )
}

