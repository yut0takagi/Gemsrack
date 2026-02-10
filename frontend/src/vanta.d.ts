declare module 'vanta/dist/vanta.halo.min' {
  type VantaEffect = { destroy?: () => void }
  type HaloFactory = (options: Record<string, unknown>) => VantaEffect
  const HALO: HaloFactory
  export default HALO
}

