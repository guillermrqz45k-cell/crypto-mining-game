import { useCallback, useEffect, useState } from 'react'
import { api, getToken, setToken, friendlyError } from './api/client.js'
import Auth from './pages/Auth.jsx'
import Layout from './components/Layout.jsx'

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [bootError, setBootError] = useState('')

  const refreshMe = useCallback(async () => {
    try {
      const me = await api.me()
      setUser(me)
      return me
    } catch (e) {
      if (e.status === 401) { setToken(null); setUser(null) }
      throw e
    }
  }, [])

  useEffect(() => {
    if (!getToken()) { setLoading(false); return }
    refreshMe().catch((e) => setBootError(friendlyError(e))).finally(() => setLoading(false))
  }, [refreshMe])

  function handleAuth(loggedUser) {
    if (loggedUser) { setUser(loggedUser); return }
    refreshMe().catch(() => {})
  }

  function logout() { setToken(null); setUser(null) }

  if (loading) return <div className="center" style={{ paddingTop: '20vh' }}><p className="spin">⚙️</p><p className="muted">Cargando CRYPTO MINING GAME…</p></div>
  if (!user) {
    return (
      <div className="main" style={{ maxWidth: 560 }}>
        {bootError && <p className="notice warn">{bootError} — Puedes iniciar sesión de nuevo.</p>}
        <Auth onAuth={handleAuth} />
      </div>
    )
  }
  return <Layout user={user} onLogout={logout} onUserChange={setUser} />
}
