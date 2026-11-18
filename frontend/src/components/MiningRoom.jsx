import { useEffect, useRef, useState } from 'react'

// Sala de minería realista: filas de mineros ASIC con ventiladores girando,
// LEDs de estado, temperatura, hashrate y consumo por equipo. Las unidades
// mostradas son las máquinas que el usuario REALMENTE posee (una por máquina
// comprada; el Minero Inicial gratis también aparece). El contador de HCK
// sube en vivo cada segundo según el hashrate real y la tasa de producción,
// y cada 100 HCK se registra un "bloque" visual derivado de esa producción.
// Sin librerías nuevas: solo CSS.
function tempFor(machine, i) {
  // Temperatura estable por equipo (derivada de su id), 58-74 °C
  let h = 0
  const s = String(machine.machine_id || machine.id || i)
  for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 97
  return 58 + (h % 17)
}

function wattsFor(hashrate) {
  return Math.max(8, Math.round(Number(hashrate || 0) * 2.2))
}

export default function MiningRoom({ machines = [], hashrate = 0, productionPerHash = 20.83, pendingHck = 0, capacityHck = 0, miningActive = false, poolBalance = null }) {
  const hckPerSecond = (Number(hashrate) * Number(productionPerHash)) / 3600
  const [livePending, setLivePending] = useState(Number(pendingHck) || 0)
  const [blocks, setBlocks] = useState([])
  const baseRef = useRef(Number(pendingHck) || 0)
  const startedRef = useRef(Date.now())
  const blockCountRef = useRef(Math.floor((Number(pendingHck) || 0) / 100))

  // Contador en vivo: sube cada segundo con la producción real
  useEffect(() => {
    baseRef.current = Number(pendingHck) || 0
    startedRef.current = Date.now()
    blockCountRef.current = Math.floor((Number(pendingHck) || 0) / 100)
    setLivePending(Number(pendingHck) || 0)
  }, [pendingHck])

  useEffect(() => {
    if (!miningActive || hckPerSecond <= 0) return
    const t = setInterval(() => {
      const elapsed = (Date.now() - startedRef.current) / 1000
      const live = Math.min(Number(capacityHck) || Infinity, baseRef.current + elapsed * hckPerSecond)
      setLivePending(live)
      const count = Math.floor(live / 100)
      if (count > blockCountRef.current) {
        const newBlocks = []
        for (let n = blockCountRef.current + 1; n <= count; n++) {
          newBlocks.push({ n, at: new Date().toLocaleTimeString('es'), hck: 100 })
        }
        blockCountRef.current = count
        setBlocks((prev) => [...newBlocks, ...prev].slice(0, 5))
      }
    }, 1000)
    return () => clearInterval(t)
  }, [miningActive, hckPerSecond, capacityHck])

  const fillPct = capacityHck > 0 ? Math.min(100, (livePending / capacityHck) * 100) : 0

  return (
    <div className="card mining-room mb">
      <div className="room-head">
        <h3>🏭 Sala de minería</h3>
        <span className={`badge ${miningActive ? 'ok' : 'warn'}`}>{miningActive ? '● MINANDO' : '○ EN PAUSA'}</span>
      </div>
      <p className="small muted">Tus equipos reales, trabajando ahora mismo. Cada unidad es una máquina que posees.</p>

      <div className="live-counter">
        <span className="coin">🪙</span>
        <b className="gold" style={{ fontSize: '1.5rem' }}>{livePending.toLocaleString('es', { maximumFractionDigits: 1 })} HCK</b>
        <span className="muted"> pendientes · +{hckPerSecond.toLocaleString('es', { maximumFractionDigits: 3 })} HCK/s</span>
      </div>
      <div className="progress green" style={{ marginTop: '.5rem' }}><div style={{ width: `${fillPct}%` }} /></div>
      <p className="small muted mt">{Number(livePending).toLocaleString('es', { maximumFractionDigits: 1 })} / {Number(capacityHck).toLocaleString('es')} HCK en el almacén ({fillPct.toFixed(0)}%)</p>

      {machines.length === 0 ? (
        <p className="empty mt">Aún no tienes equipos en la sala. Tu Minero Inicial aparece aquí al registrarte.</p>
      ) : (
        <div className="asic-grid mt">
          {machines.map((m, i) => {
            const hr = Number(m.hashrate ?? 0)
            const temp = tempFor(m, i)
            const watts = wattsFor(hr)
            const hot = temp >= 70
            return (
              <div key={m.id ?? i} className="asic-unit">
                <div className="asic-top">
                  <div className={`fan ${miningActive ? 'spinning' : ''}`}><span>✦</span></div>
                  <div className={`fan ${miningActive ? 'spinning slow' : ''}`}><span>✦</span></div>
                  <div className="leds">
                    <span className={`led ${miningActive ? 'green' : 'amber'}`} />
                    <span className={`led ${miningActive ? 'green blink' : 'off'}`} />
                    <span className={`led ${hot ? 'red blink' : 'green'}`} />
                  </div>
                </div>
                <div className="asic-body">
                  <b>{m.name || `Máquina ${m.machine_id || ''}`}</b>
                  <p className="small">⚡ {hr.toLocaleString('es')} H/s</p>
                  <p className="small">🌡️ {temp} °C {hot && <span className="badge warn">caliente</span>}</p>
                  <p className="small">🔌 {watts.toLocaleString('es')} W</p>
                  <p className="small muted">{miningActive ? '⛏️ Minando…' : '⏸️ En pausa'}</p>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {blocks.length > 0 && (
        <div className="block-log mt">
          <h4>🧱 Bloques minados</h4>
          {blocks.map((b) => (
            <p key={b.n} className="small">⛏️ Bloque #{b.n.toLocaleString('es')} · +{b.hck} HCK · {b.at}</p>
          ))}
        </div>
      )}

      {poolBalance !== null && poolBalance !== undefined && (
        <p className="small muted mt">💰 Fondo de recompensas del proyecto: <b className="gold">${Number(poolBalance).toLocaleString('es', { minimumFractionDigits: 2 })} USDT</b> · Los retiros se pagan solo desde este fondo real.</p>
      )}
    </div>
  )
}
