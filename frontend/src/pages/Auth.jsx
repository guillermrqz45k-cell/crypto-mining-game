import { useState } from 'react'
import { api, setToken, friendlyError } from '../api/client.js'

export default function Auth({ onAuth }) {
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [referralCode, setReferralCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (username.trim().length < 3) return setError('El usuario debe tener al menos 3 caracteres.')
    if (password.length < 6) return setError('La contraseña debe tener al menos 6 caracteres.')
    setLoading(true)
    try {
      const data = mode === 'login'
        ? await api.login({ username: username.trim(), password })
        : await api.register({ username: username.trim(), password, referral_code: referralCode.trim() || undefined })
      if (!data?.access_token) throw new Error('El servidor no devolvió un token de acceso.')
      setToken(data.access_token)
      onAuth(data.user || null)
    } catch (err) {
      setError(friendlyError(err))
    } finally { setLoading(false) }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-logo">⛏️</div>
      <h1 className="center"><span className="gold">CRYPTO MINING GAME</span></h1>
      <p className="center muted mb">Minería virtual · Gana HCK · Compra máquinas · Sube de nivel</p>
      <div className="card">
        <div className="tabs">
          <button className={`tab ${mode === 'login' ? 'active' : ''}`} onClick={() => setMode('login')}>Iniciar sesión</button>
          <button className={`tab ${mode === 'register' ? 'active' : ''}`} onClick={() => setMode('register')}>Crear cuenta</button>
        </div>
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="username">Usuario</label>
            <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="tu_usuario" autoComplete="username" />
          </div>
          <div className="field">
            <label htmlFor="password">Contraseña</label>
            <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
          </div>
          {mode === 'register' && (
            <div className="field">
              <label htmlFor="referral">Código de referido (opcional)</label>
              <input id="referral" value={referralCode} onChange={(e) => setReferralCode(e.target.value)} placeholder="Ej. AMO123" />
              <span className="hint">Si alguien te invitó, escribe su código y ambos ganáis recompensas.</span>
            </div>
          )}
          {error && <p className="error">{error}</p>}
          <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
            {loading ? 'Cargando…' : mode === 'login' ? 'Entrar a minar ⛏️' : 'Crear mi cuenta'}
          </button>
        </form>
      </div>
      <p className="footer">Minería virtual. Las recompensas dependen del fondo de recompensas disponible. Sin rentabilidad garantizada.</p>
    </div>
  )
}
