import { useCallback, useEffect, useRef, useState } from 'react'
import { api, friendlyError } from '../api/client.js'
import ProductionChart from '../components/ProductionChart.jsx'
import Confetti from '../components/Confetti.jsx'

function useAnimatedNumber(target) {
  const [v, setV] = useState(target || 0)
  const prev = useRef(target || 0)
  useEffect(() => {
    const from = prev.current, to = target || 0
    if (from === to) return
    const start = performance.now()
    let raf
    const tick = (t) => {
      const p = Math.min(1, (t - start) / 600)
      setV(from + (to - from) * p)
      if (p < 1) raf = requestAnimationFrame(tick); else prev.current = to
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target])
  return v
}

export default function Dashboard({ user, onUserChange }) {
  const [status, setStatus] = useState(null)
  const [chart, setChart] = useState([])
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [levelUp, setLevelUp] = useState(false)
  const animatedHck = useAnimatedNumber(status?.pending_hck ?? 0)

  const load = useCallback(async () => {
    try {
      const s = await api.miningStatus()
      setStatus(s)
    } catch (e) { setError(friendlyError(e)) }
    try {
      const st = await api.stats()
      const arr = st?.production_last_14_days || st?.production || st?.history || st?.daily || []
      setChart(Array.isArray(arr) ? arr : [])
    } catch { /* el gráfico es opcional: si /api/stats no existe, se muestra el aviso vacío */ }
  }, [])

  useEffect(() => { load() }, [load])
  // Refresco suave mientras mina (el saldo pendiente crece).
  useEffect(() => {
    if (!status?.mining_active) return
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [status?.mining_active, load])

  async function toggleMining() {
    setBusy(true); setMsg(''); setError('')
    try {
      const res = status?.mining_active ? await api.miningStop() : await api.miningStart()
      setMsg(status?.mining_active ? 'Minería detenida. Recolecta tus HCK antes de que el almacén se llene.' : '¡Minería iniciada! Tus máquinas ya están generando HCK.')
      if (res) setStatus((s) => ({ ...(s || {}), ...res, mining_active: !status?.mining_active }))
      await load()
    } catch (e) { setError(friendlyError(e)) } finally { setBusy(false) }
  }

  async function collect() {
    setBusy(true); setMsg(''); setError('')
    try {
      const res = await api.miningCollect()
      const gained = res?.collected_hck ?? 0
      setMsg(`¡Recolectaste ${Number(gained).toLocaleString('es')} HCK!${res?.xp_gained ? ` +${res.xp_gained} XP.` : ''}`)
      if (res?.level_up) {
        setLevelUp(true)
        setTimeout(() => setLevelUp(false), 3000)
      }
      await load()
      const me = await api.me().catch(() => null)
      if (me) onUserChange(me)
    } catch (e) { setError(friendlyError(e)) } finally { setBusy(false) }
  }

  const pending = status?.pending_hck ?? 0
  const capacity = status?.capacity_hck ?? 0
  const fillPct = capacity > 0 ? Math.min(100, (pending / capacity) * 100) : 0
  const xp = user?.xp ?? 0
  const level = user?.level ?? 1
  const xpForLevel = 100 * level
  const xpPct = Math.min(100, (xp % xpForLevel) / xpForLevel * 100)

  return (
    <div>
      <Confetti show={levelUp} />
      <div className="page-head">
        <h1>⛏️ Centro de minería</h1>
        <p>Tu granja virtual está {status?.mining_active ? 'trabajando' : 'en pausa'}. Recolecta antes de que el almacén se llene.</p>
      </div>
      {error && <p className="notice danger">{error}</p>}
      {msg && <p className="notice ok">{msg}</p>}
      {levelUp && <p className="notice warn pop">🎉 ¡SUBISTE DE NIVEL! Ahora eres nivel {level}.</p>}

      <div className="grid grid4 mb">
        <div className="card stat"><div className="label">Saldo HCK</div><div className="value gold">🪙 {(user?.hck_balance ?? 0).toLocaleString('es')}</div><div className="sub">Moneda del juego</div></div>
        <div className="card stat"><div className="label">Saldo USDT</div><div className="value cyan">${(user?.usdt_balance ?? 0).toLocaleString('es', { minimumFractionDigits: 2 })}</div><div className="sub">Para comprar máquinas</div></div>
        <div className="card stat"><div className="label">Hashrate total</div><div className="value">{(status?.hashrate ?? user?.hashrate ?? 0).toLocaleString('es')} H/s</div><div className="sub">Suma de tus máquinas</div></div>
        <div className="card stat"><div className="label">Nivel {level}</div><div className="value">{xp.toLocaleString('es')} XP</div><div className="sub">{xpForLevel - (xp % xpForLevel)} XP para el nivel {level + 1}</div></div>
      </div>

      <div className="card mb">
        <div className="label small muted">PROGRESO DE NIVEL</div>
        <div className="progress mt" style={{ marginTop: '.4rem' }}><div style={{ width: `${xpPct}%` }} /></div>
        <p className="small muted mt">Nivel {level} · {xpPct.toFixed(0)}% hacia el nivel {level + 1}</p>
      </div>

      <div className="card mine-wrap mb">
        {status?.mining_active && <><span className="particle" style={{ left: '12%', top: '18%' }}>✨</span><span className="particle" style={{ right: '14%', top: '26%', animationDelay: '.8s' }}>🪙</span><span className="particle" style={{ left: '20%', bottom: '20%', animationDelay: '1.4s' }}>⚡</span><span className="particle" style={{ right: '20%', bottom: '14%', animationDelay: '.4s' }}>✨</span></>}
        <button className={`mine-btn ${status?.mining_active ? 'mining' : 'stopped'}`} onClick={toggleMining} disabled={busy}>
          {status?.mining_active ? <><span className="spin">⚙️</span><span className="big">MINANDO…</span>Toca para detener</> : <><span className="big">⛏️</span><span className="big">MINAR</span>Toca para iniciar</>}
        </button>
        <p className="mt"><span className="coin">🪙</span> <b className="gold" style={{ fontSize: '1.3rem' }}>{animatedHck.toLocaleString('es', { maximumFractionDigits: 1 })} HCK</b> <span className="muted">pendientes de recolectar</span></p>
        <p className="small muted">Hashrate: {(status?.hashrate ?? user?.hashrate ?? 0).toLocaleString('es')} H/s{status?.started_at ? ` · Minando desde ${new Date(status.started_at).toLocaleString('es')}` : ''}</p>
        <div className="row" style={{ justifyContent: 'center', marginTop: '1rem' }}>
          <button className="btn btn-gold" onClick={collect} disabled={busy || pending <= 0}>💰 RECOLECTAR {pending > 0 ? `(${Number(pending).toLocaleString('es')} HCK)` : ''}</button>
        </div>
      </div>

      <div className="card mb">
        <h3>📦 Almacén de HCK</h3>
        <p className="small muted">{Number(pending).toLocaleString('es')} / {Number(capacity).toLocaleString('es')} HCK</p>
        <div className={`progress ${fillPct > 85 ? 'gold' : 'green'}`} style={{ marginTop: '.5rem' }}><div style={{ width: `${fillPct}%` }} /></div>
        {(status?.storage_full || fillPct >= 100) && <p className="notice warn mt">⚠️ El almacén está lleno: tus máquinas han dejado de generar HCK. ¡Recolecta ahora!</p>}
        {fillPct >= 80 && fillPct < 100 && <p className="notice warn mt">⚠️ El almacén está casi lleno ({fillPct.toFixed(0)}%). Recolecta antes de que se llene.</p>}
        {fillPct < 80 && <p className="small muted mt">Cuando el almacén se llena, la producción se detiene hasta que recolectes.</p>}
      </div>

      <div className="card">
        <h3>📈 Producción de los últimos 14 días</h3>
        <ProductionChart data={chart} />
      </div>
    </div>
  )
}
