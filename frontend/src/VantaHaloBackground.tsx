import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'

type VantaEffect = {
  destroy?: () => void
}

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return true
  return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false
}

export function VantaHaloBackground() {
  const elRef = useRef<HTMLDivElement | null>(null)
  const effectRef = useRef<VantaEffect | null>(null)
  const [enabled, setEnabled] = useState(false)

  // 初期表示のチラつきを抑えるために、マウント後にON
  useEffect(() => {
    if (prefersReducedMotion()) return
    setEnabled(true)
  }, [])

  const fallbackStyle = useMemo(() => {
    return {
      background:
        'radial-gradient(1200px 600px at 50% 10%, rgba(99,102,241,0.20), rgba(0,0,0,0)), radial-gradient(900px 500px at 30% 70%, rgba(34,211,238,0.14), rgba(0,0,0,0)), radial-gradient(900px 500px at 70% 70%, rgba(244,114,182,0.10), rgba(0,0,0,0)), #05070f',
    } as const
  }, [])

  useEffect(() => {
    if (!enabled) return
    if (!elRef.current) return

    let alive = true

    ;(async () => {
      // vanta は minified bundle なので dynamic import にしておく（SSR/テストでも安全）
      const mod: any = await import('vanta/dist/vanta.halo.min')
      if (!alive) return
      const HALO = mod?.default ?? mod
      if (typeof HALO !== 'function') return

      // 既存があれば破棄
      effectRef.current?.destroy?.()

      effectRef.current = HALO({
        el: elRef.current,
        THREE,
        mouseControls: true,
        touchControls: true,
        gyroControls: false,
        minHeight: 200.0,
        minWidth: 200.0,
        backgroundColor: 0x05070f,
        baseColor: 0x1f2a5a,
        // Halo固有（見た目をテック寄りに）
        amplitudeFactor: 0.7,
        xOffset: 0.0,
        yOffset: 0.0,
        size: 1.2,
      })
    })().catch(() => {
      // 失敗時はフォールバックだけでOK
    })

    return () => {
      alive = false
      effectRef.current?.destroy?.()
      effectRef.current = null
    }
  }, [enabled])

  return (
    <div className="fixed inset-0 -z-10">
      <div className="absolute inset-0" style={fallbackStyle} />
      {/* vanta canvas はこの要素配下に生成される */}
      <div ref={elRef} className="absolute inset-0" />
      {/* 上から薄いグリッド/ノイズっぽさ */}
      <div className="pointer-events-none absolute inset-0 opacity-20 [background-image:linear-gradient(rgba(255,255,255,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.06)_1px,transparent_1px)] [background-size:56px_56px]" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/40 via-black/30 to-black/70" />
    </div>
  )
}

