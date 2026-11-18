import { useEffect, useState } from 'react'
import { api, friendlyError } from '../api/client.js'

export default function Referrals() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.referrals()
      .then((d) => setData(d))
      .catch((e) => setError(friendlyError(e)))
  }, [])

  const link = data?.referral_link || (data?.referral_code ? `${window.location.origin}/?ref=${data.referral_code}` : '')
  const users = data?.referred_users || []

  function copy() {
    if (!link) return
    navigator.clipboard?.writeText(link).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) }).catch(() => {})
  }

  return (
    <div>
      <div className="page-head"><h1>👥 Referidos</h1><p>Invita amigos con tu enlace y gana HCK por cada referido.</p></div>
      {error && <p className="notice danger">{error}</p>}
      <div className="grid grid3 mb">
        <div className="card stat"><div className="label">Tu código</div><div className="value gold">{data?.referral_code || '—'}</div></div>
        <div className="card stat"><div className="label">Referidos</div><div className="value">{data?.referred_count ?? users.length ?? 0}</div></div>
        <div className="card stat"><div className="label">HCK ganado</div><div className="value gold">🪙 {Number(data?.earned_hck ?? 0).toLocaleString('es')}</div></div>
      </div>
      <div className="card mb">
        <h3>Tu enlace de invitación</h3>
        <div className="code-box mt">{link || 'Cargando…'}</div>
        <button className="btn btn-primary mt" onClick={copy} disabled={!link}>{copied ? '✓ Copiado' : '📋 Copiar enlace'}</button>
        <p className="small muted mt">Comparte el enlace: quien se registre con tu código queda como tu referido.</p>
      </div>
      <div className="card">
        <h3>Mis referidos</h3>
        {users.length === 0 ? <p className="empty">Aún no tienes referidos. ¡Comparte tu enlace!</p> : (
          <div className="table-wrap"><table>
            <thead><tr><th>Usuario</th><th>Fecha</th><th>HCK ganado</th></tr></thead>
            <tbody>{users.map((u, i) => (
              <tr key={u.id ?? i}>
                <td>{u.username || u.name || '—'}</td>
                <td>{u.created_at || u.joined_at ? new Date(u.created_at || u.joined_at).toLocaleDateString('es') : '—'}</td>
                <td>{Number(u.earned_hck ?? u.reward_hck ?? 0).toLocaleString('es')} HCK</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </div>
    </div>
  )
}
