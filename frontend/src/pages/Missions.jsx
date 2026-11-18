import { useEffect, useState } from 'react'
import { api, friendlyError } from '../api/client.js'

export default function Missions({ onUserChange }) {
  const [missions, setMissions] = useState([])
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [streak, setStreak] = useState(0)
  const [bonusClaimed, setBonusClaimed] = useState(false)

  async function load() {
    try {
      const m = await api.missions()
      setMissions(Array.isArray(m) ? m : m?.missions || [])
    } catch (e) { setError(friendlyError(e)); setMissions([]) }
  }
  useEffect(() => { load() }, [])

  async function claim(m) {
    setBusyId(m.id); setMsg(''); setError('')
    try {
      const res = await api.claimMission(m.id)
      setMsg(`¡Misión completada! Ganaste ${Number(res?.reward_hck ?? m.reward_hck ?? 0).toLocaleString('es')} HCK.`)
      const me = await api.me().catch(() => null)
      if (me) onUserChange(me)
      await load()
    } catch (e) { setError(friendlyError(e)) } finally { setBusyId(null) }
  }

  async function claimBonus() {
    setBusyId('bonus'); setMsg(''); setError('')
    try {
      const res = await api.claimDailyBonus()
      setStreak(res?.streak ?? streak + 1)
      setBonusClaimed(true)
      setMsg(`¡Bono diario reclamado! +${Number(res?.bonus_hck ?? 0).toLocaleString('es')} HCK · Racha: ${res?.streak ?? streak + 1} día(s).`)
      const me = await api.me().catch(() => null)
      if (me) onUserChange(me)
    } catch (e) { setError(friendlyError(e)) } finally { setBusyId(null) }
  }

  const today = streak > 0 ? ((streak - 1) % 7) + 1 : 1
  return (
    <div>
      <div className="page-head"><h1>🎯 Misiones</h1><p>Completa misiones diarias, gana HCK y mantén tu racha.</p></div>
      {error && <p className="notice danger">{error}</p>}
      {msg && <p className="notice ok">{msg}</p>}

      <div className="card mb center">
        <h2>🎁 Bono diario</h2>
        <p className="small muted">Reclama cada día y aumenta tu racha. La racha se reinicia si fallas un día.</p>
        <div className="streak">
          {[1, 2, 3, 4, 5, 6, 7].map((d) => (
            <div key={d} className={`day-circle ${d < today ? 'done' : ''} ${d === today ? 'today' : ''}`}>
              <b>{d < today ? '✓' : d}</b>Día {d}
            </div>
          ))}
        </div>
        <p className="small">Racha actual: <b className="gold">{streak} día(s)</b></p>
        <button className="btn btn-gold mt" onClick={claimBonus} disabled={busyId === 'bonus' || bonusClaimed}>
          {bonusClaimed ? '✓ Bono de hoy reclamado' : busyId === 'bonus' ? 'Reclamando…' : 'Reclamar bono diario'}
        </button>
      </div>

      <h2 className="mb">Misiones diarias</h2>
      {missions.length === 0 ? (
        <p className="empty">No hay misiones disponibles ahora mismo. Vuelve mañana: las misiones se renuevan cada día.</p>
      ) : (
        <div className="grid grid2">
          {missions.map((m) => {
            const progress = Number(m.progress ?? 0)
            const target = Number(m.target ?? 1)
            const pct = Math.min(100, (progress / target) * 100)
            const done = m.completed || progress >= target
            return (
              <div key={m.id} className="card">
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <h3>{m.title}</h3>
                  {m.claimed ? <span className="badge ok">Reclamada</span> : done ? <span className="badge warn">Lista</span> : <span className="badge info">En curso</span>}
                </div>
                <p className="small muted mt">{m.description || ''}</p>
                <p className="small mt">Progreso: {progress} / {target}</p>
                <div className="progress" style={{ margin: '.4rem 0 .8rem' }}><div style={{ width: `${pct}%` }} /></div>
                <p className="gold"><b>Recompensa: {Number(m.reward_hck ?? 0).toLocaleString('es')} HCK</b></p>
                <button className="btn btn-primary mt" disabled={!done || m.claimed || busyId === m.id} onClick={() => claim(m)}>
                  {m.claimed ? '✓ Ya reclamada' : busyId === m.id ? 'Reclamando…' : done ? 'Reclamar recompensa' : 'Aún no completada'}
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
