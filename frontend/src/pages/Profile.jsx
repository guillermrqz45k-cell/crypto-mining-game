import { apiUrl } from '../api/client.js'

export default function Profile({ user, onLogout }) {
  return (
    <div>
      <div className="page-head"><h1>👤 Perfil</h1><p>Tu cuenta en CRYPTO MINING GAME.</p></div>
      <div className="card mb">
        <div className="grid grid2">
          <div><p className="small muted">USUARIO</p><p><b>{user?.username}</b> {user?.is_admin && <span className="badge admin">ADMIN</span>}</p></div>
          <div><p className="small muted">CÓDIGO DE REFERIDO</p><p className="mono">{user?.referral_code || '—'}</p></div>
          <div><p className="small muted">NIVEL</p><p><b>{user?.level ?? 1}</b> · {Number(user?.xp ?? 0).toLocaleString('es')} XP</p></div>
          <div><p className="small muted">HASHRATE</p><p><b>{Number(user?.hashrate ?? 0).toLocaleString('es')} H/s</b></p></div>
          <div><p className="small muted">SALDO HCK</p><p className="gold"><b>🪙 {Number(user?.hck_balance ?? 0).toLocaleString('es')}</b></p></div>
          <div><p className="small muted">SALDO USDT</p><p className="cyan"><b>${Number(user?.usdt_balance ?? 0).toLocaleString('es', { minimumFractionDigits: 2 })}</b></p></div>
        </div>
      </div>
      <div className="card mb">
        <h3>Servidor de la API</h3>
        <p className="small muted mt mono">{apiUrl}</p>
        <p className="small muted">Si la app no carga datos, comprueba que el backend esté en marcha en esa URL (variable VITE_API_URL).</p>
      </div>
      <button className="btn btn-danger" onClick={onLogout}>🚪 Cerrar sesión</button>
    </div>
  )
}
