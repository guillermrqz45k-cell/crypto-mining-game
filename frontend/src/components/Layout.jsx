import { useState } from 'react'
import Dashboard from '../pages/Dashboard.jsx'
import Machines from '../pages/Machines.jsx'
import Missions from '../pages/Missions.jsx'
import Wallet from '../pages/Wallet.jsx'
import Withdrawals from '../pages/Withdrawals.jsx'
import Referrals from '../pages/Referrals.jsx'
import Leaderboard from '../pages/Leaderboard.jsx'
import Profile from '../pages/Profile.jsx'
import Admin from '../pages/Admin.jsx'

const NAV = [
  { id: 'dashboard', label: 'Minar', icon: '⛏️' },
  { id: 'machines', label: 'Máquinas', icon: '🖥️' },
  { id: 'missions', label: 'Misiones', icon: '🎯' },
  { id: 'wallet', label: 'Billetera', icon: '👛' },
  { id: 'withdrawals', label: 'Retiros', icon: '💸' },
  { id: 'referrals', label: 'Referidos', icon: '👥' },
  { id: 'leaderboard', label: 'Top', icon: '🏆' },
  { id: 'profile', label: 'Perfil', icon: '👤' },
]
const MOBILE_NAV = ['dashboard', 'machines', 'missions', 'wallet', 'profile']

export default function Layout({ user, onLogout, onUserChange }) {
  const [page, setPage] = useState('dashboard')
  const nav = [...NAV]
  if (user?.is_admin) nav.push({ id: 'admin', label: 'Admin', icon: '🛡️' })

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="logo">⛏️ <span>CRYPTO MINING GAME</span></div>
        <p className="small gold">Creador por Dark Mous</p>
        <p className="small muted">Hola, <b style={{ color: 'var(--text)' }}>{user?.username}</b> · Nivel {user?.level ?? 1}</p>
        {nav.map((n) => (
          <button key={n.id} className={`navlink ${page === n.id ? 'active' : ''}`} onClick={() => setPage(n.id)}>
            <span className="ico">{n.icon}</span>{n.label}
            {n.id === 'admin' && <span className="badge admin" style={{ marginLeft: 'auto' }}>ADMIN</span>}
          </button>
        ))}
        <div className="spacer" />
        <button className="navlink" onClick={onLogout}><span className="ico">🚪</span>Cerrar sesión</button>
      </aside>

      <main className="main">
        {page === 'dashboard' && <Dashboard user={user} onUserChange={onUserChange} />}
        {page === 'machines' && <Machines user={user} onUserChange={onUserChange} />}
        {page === 'missions' && <Missions user={user} onUserChange={onUserChange} />}
        {page === 'wallet' && <Wallet user={user} onUserChange={onUserChange} />}
        {page === 'withdrawals' && <Withdrawals user={user} />}
        {page === 'referrals' && <Referrals />}
        {page === 'leaderboard' && <Leaderboard />}
        {page === 'profile' && <Profile user={user} onLogout={onLogout} />}
        {page === 'admin' && user?.is_admin && <Admin />}
        <footer className="footer">
          Creador por Dark Mous
          <br />Minería virtual. Las recompensas dependen del fondo de recompensas disponible. Sin rentabilidad garantizada.
          <br />CRYPTO MINING GAME · HCK es una moneda virtual del juego, no un activo financiero.
        </footer>
      </main>

      <nav className="bottomnav" aria-label="Navegación principal">
        {MOBILE_NAV.map((id) => {
          const n = NAV.find((x) => x.id === id)
          return (
            <button key={id} className={page === id ? 'active' : ''} onClick={() => setPage(id)}>
              <span className="ico">{n.icon}</span>{n.label}
            </button>
          )
        })}
      </nav>
    </div>
  )
}
