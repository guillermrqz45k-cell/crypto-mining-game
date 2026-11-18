import { useEffect, useState } from 'react'
import { api, friendlyError } from '../api/client.js'

const FALLBACK = [
  { id: 'level_0', name: 'Minero Inicial', price_usdt: 0, hashrate: 5, level: 0, is_starter: true, description: 'Gratis: lo recibes al registrarte. Empieza a minar HCK.', icon: '🌱' },
  { id: 'level_1', name: 'Minero USB', price_usdt: 10, hashrate: 10, level: 1, description: 'Ideal para empezar a minar HCK.', icon: '🔌' },
  { id: 'level_2', name: 'Rig GPU', price_usdt: 50, hashrate: 60, level: 2, description: 'Un paso más: más potencia por USDT.', icon: '💻' },
  { id: 'level_3', name: 'ASIC S9', price_usdt: 150, hashrate: 200, level: 3, description: 'Potencia seria para granjas medianas.', icon: '🖥️' },
  { id: 'level_4', name: 'Granja ASIC', price_usdt: 350, hashrate: 500, level: 4, description: 'Granja de ASICs: producción seria.', icon: '🏭' },
  { id: 'level_5', name: 'Rig Cuántico', price_usdt: 750, hashrate: 1200, level: 5, description: 'Potencia cuántica para granjas grandes.', icon: '⚡' },
  { id: 'level_6', name: 'Centro de Datos', price_usdt: 1400, hashrate: 2500, level: 6, description: 'Un centro de datos completo a tu servicio.', icon: '🏢' },
  { id: 'level_7', name: 'Granja Cuántica', price_usdt: 2800, hashrate: 5500, level: 7, description: 'Granja cuántica de élite. Producción masiva.', icon: '🌌' },
  { id: 'level_8', name: 'Núcleo HCK', price_usdt: 5000, hashrate: 12000, level: 8, description: 'El núcleo definitivo del juego. Potencia máxima.', icon: '🚀' },
]

export default function Machines({ user, onUserChange }) {
  const [catalog, setCatalog] = useState([])
  const [mine, setMine] = useState([])
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [usedFallback, setUsedFallback] = useState(false)

  async function load() {
    try {
      const c = await api.machines()
      const list = Array.isArray(c) ? c : c?.machines || []
      setCatalog(list.length ? list : FALLBACK)
      if (!list.length) setUsedFallback(true)
    } catch (e) { setCatalog(FALLBACK); setUsedFallback(true); setError(friendlyError(e)) }
    try {
      const m = await api.myMachines()
      setMine(Array.isArray(m) ? m : m?.machines || [])
    } catch { setMine([]) }
  }
  useEffect(() => { load() }, [])

  async function buy(m) {
    setBusyId(`buy-${m.id}`); setMsg(''); setError('')
    try {
      await api.buyMachine(m.id)
      setMsg(`¡Compraste ${m.name}! Ya está minando para ti.`)
      const me = await api.me().catch(() => null)
      if (me) onUserChange(me)
      await load()
    } catch (e) { setError(friendlyError(e)) } finally { setBusyId(null) }
  }
  async function upgrade(m) {
    setBusyId(`up-${m.id}`); setMsg(''); setError('')
    try {
      await api.upgradeMachine(m.id)
      setMsg(`¡Overclock mejorado en ${m.name || 'tu máquina'}! Más hashrate.`)
      await load()
    } catch (e) { setError(friendlyError(e)) } finally { setBusyId(null) }
  }

  const balance = user?.usdt_balance ?? 0
  return (
    <div>
      <div className="page-head"><h1>🖥️ Máquinas de minería</h1><p>Tu saldo: <b className="cyan">${Number(balance).toLocaleString('es', { minimumFractionDigits: 2 })} USDT</b> · Más hashrate = más HCK por hora.</p></div>
      {error && <p className="notice danger">{error}</p>}
      {msg && <p className="notice ok">{msg}</p>}
      {usedFallback && <p className="notice warn">El catálogo del servidor no respondió; se muestran las 9 máquinas de referencia. Los precios reales los define el backend.</p>}

      <h2 className="mb">Catálogo</h2>
      <div className="grid grid3 mb">
        {catalog.map((m) => {
          const price = Number(m.price_usdt ?? 0)
          const isStarter = m.is_starter || m.id === 'level_0' || price === 0
          const ownedStarter = isStarter && mine.some((x) => x.machine_id === 'level_0')
          const cant = !isStarter && balance < price
          const level = m.level ?? (typeof m.id === 'string' && m.id.startsWith('level_') ? Number(m.id.split('_')[1]) : null)
          return (
            <div key={m.id} className="card machine-card">
              <span className="machine-icon">{m.icon || '⛏️'}</span>
              <h3>{m.name}</h3>
              {level !== null && <p><span className="badge info">Nivel {level}</span>{isStarter && <span className="badge ok"> GRATIS</span>}</p>}
              <p className="small muted">{m.description || ''}</p>
              <p>⚡ <b>{Number(m.hashrate ?? 0).toLocaleString('es')} H/s</b></p>
              <p className="price">{isStarter ? 'GRATIS' : `$${price.toLocaleString('es', { minimumFractionDigits: 2 })} USDT`}</p>
              <button className="btn btn-primary btn-block" disabled={cant || ownedStarter || busyId === `buy-${m.id}`} onClick={() => buy(m)}>
                {busyId === `buy-${m.id}` ? 'Procesando…' : ownedStarter ? 'Activo ✓' : isStarter ? 'Reclamar gratis' : cant ? 'Saldo insuficiente' : 'Comprar'}
              </button>
              {cant && <p className="small muted center">Te faltan ${(price - balance).toLocaleString('es', { minimumFractionDigits: 2 })} USDT. Deposita en Billetera.</p>}
            </div>
          )
        })}
      </div>

      <h2 className="mb">Mis máquinas ({mine.length})</h2>
      {mine.length === 0 ? (
        <p className="empty">Aún no tienes máquinas. Tu Minero Inicial (nivel 0, gratis) se activa al registrarte; si no lo ves, reclámalo arriba en el catálogo.</p>
      ) : (
        <div className="grid grid3">
          {mine.map((m) => {
            const isStarter = m.machine_id === 'level_0'
            return (
            <div key={m.id} className="card machine-card">
              <h3>{m.name || `Máquina #${m.machine_id ?? m.id}`}</h3>
              <p>⚡ <b>{Number(m.hashrate ?? 0).toLocaleString('es')} H/s</b></p>
              <p>Overclock: <span className="badge info">Nivel {m.overclock_level ?? 0}</span></p>
              {isStarter ? (
                <p className="small muted center">El Minero Inicial no admite overclock.</p>
              ) : (
                <button className="btn btn-gold btn-block" disabled={busyId === `up-${m.id}`} onClick={() => upgrade(m)}>
                  {busyId === `up-${m.id}` ? 'Mejorando…' : '⬆️ Mejorar (overclock)'}
                </button>
              )}
            </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
