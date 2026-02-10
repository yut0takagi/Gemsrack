import { useEffect, useState } from 'react'
import { AdminPanel } from './AdminPanel'
import { VantaHaloBackground } from './VantaHaloBackground'
import { adminMe } from './api'

export function AdminApp() {
  const [adminEnabled, setAdminEnabled] = useState(true)

  useEffect(() => {
    const ac = new AbortController()
    adminMe({ signal: ac.signal })
      .then((r) => setAdminEnabled(Boolean(r.enabled)))
      .catch(() => setAdminEnabled(false))
    return () => ac.abort()
  }, [])

  return (
    <div className="relative min-h-screen text-slate-100">
      <VantaHaloBackground />

      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md">
          <div className="flex flex-col gap-3 p-5 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
              <div className="text-lg font-semibold tracking-wide">
                <span className="bg-gradient-to-r from-fuchsia-300 via-indigo-300 to-cyan-300 bg-clip-text text-transparent">
                  Gemsrack Admin
                </span>
              </div>
              <div className="text-sm text-slate-300">
                {adminEnabled ? '管理画面（ログイン必須）' : 'Adminは無効です（ADMIN_PASSWORD未設定）'}
              </div>
            </div>

            <a
              href="/"
              className="inline-flex h-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-semibold text-slate-100 hover:bg-white/10"
            >
              公開ページへ
            </a>
          </div>
        </div>

        <div className="mt-6">
          <AdminPanel />
        </div>

        <footer className="mt-8 text-center text-xs text-slate-500">
          <span className="font-mono">/api/admin</span>（セッション認証）
        </footer>
      </div>
    </div>
  )
}

