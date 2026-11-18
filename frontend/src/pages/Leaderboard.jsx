import { useEffect, useState } from 'react'
import { api, friendlyError } from '../api/client.js'

export default function Leaderboard() {
  const [mode, setMode] = useState('hck')
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    api.leaderboard()
      .then((d) => {
        const list = Array.isArray(d) ? d : d?.leaderboard || d?.top || d?.users || []
        setRows(list)
      })
      .catch((e) => setError(friendlyError(e)))
  }, [])

  const sorted = [...rows].sort((a, b) => {
    const ka = mode === 'hck' ? Number(a.hck_balance ?? a.hck ?? a.score ?? 0) : Number(a.hashrate ?? 0)
    const kb = mode === 'hck' ? Number(b.hck_balance ?? b.hck ?? b.score ?? 0) : Number(b.hashrate ?? 0)
    return kb - ka
  }).slice(0, 20)

  const medal = (i) => (i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}.`)

  return (
    <div>
      <div className="page-head"><h1>🏆 Clasificación</h1><p>Los 20 mejores mineros del juego.</p></div>
      {error && <p className="notice danger">{error}</p>}
      <div className="tabs">
        <button className={`tab ${mode === 'hck' ? 'active' : ''}`} onClick={() => setMode('hck')}>Por HCK 🪙</button>
        <button className={`tab ${mode === 'hashrate' ? 'active' : ''}`} onClick={() => setMode('hashrate')}>Por hashrate ⚡</button>
      </div>
      <div className="card">
        {sorted.length === 0 ? <p className="empty">Aún no hay clasificación disponible.</p> : (
          <div className="table-wrap"><table>
            <thead><tr><th>#</th><th>Usuario</th><th>Nivel</th><th>HCK</th><th>Hashrate</th></tr></thead>
            <tbody>{sorted.map((u, i) => (
              <tr key={u.id ?? u.username ?? i}>
                <td>{medal(i)}</td>
                <td><b>{u.username || '—'}</b></td>
                <td>{u.level ?? '—'}</td>
                <td className="gold">{Number(u.hck_balance ?? u.hck ?? 0).toLocaleString('es')} HCK</td>
                <td>{Number(u.hashrate ?? 0).toLocaleString('es')} H/s</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </div>
    </div>
  )
}
