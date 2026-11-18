import { useEffect, useState } from 'react'
import { api, friendlyError } from '../api/client.js'

// Panel de administración. El admin NUNCA ve ni maneja claves privadas:
// el pago on-chain lo hace desde su propia wallet y aquí solo registra el tx_hash.
const TABS = [
  { id: 'users', label: 'Usuarios' },
  { id: 'deposits', label: 'Depósitos' },
  { id: 'withdrawals', label: 'Retiros' },
  { id: 'pool', label: 'Fondo de recompensas' },
  { id: 'config', label: 'Configuración' },
  { id: 'audit', label: 'Auditoría' },
  { id: 'fraud', label: 'Alertas de fraude' },
]

export default function Admin() {
  const [tab, setTab] = useState('users')
  const [data, setData] = useState(null)
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [txHash, setTxHash] = useState({})
  const [fundAmount, setFundAmount] = useState('')
  const [config, setConfig] = useState({})

  async function load(t = tab) {
    setError(''); setMsg('')
    try {
      if (t === 'users') { const d = await api.adminUsers(); setData(Array.isArray(d) ? d : d?.users || []) }
      if (t === 'deposits') { const d = await api.adminDeposits(); setData(Array.isArray(d) ? d : d?.deposits || []) }
      if (t === 'withdrawals') { const d = await api.adminWithdrawals(); setData(Array.isArray(d) ? d : d?.withdrawals || []) }
      if (t === 'pool') { const d = await api.adminRewardPool(); setData(d) }
      if (t === 'config') { const d = await api.adminConfig(); setData(d); setConfig(d || {}) }
      if (t === 'audit') { const d = await api.adminAudit(); setData(Array.isArray(d) ? d : d?.events || d?.audit || []) }
      if (t === 'fraud') { const d = await api.adminFraudAlerts(); setData(Array.isArray(d) ? d : d?.alerts || []) }
    } catch (e) { setError(friendlyError(e)); setData(null) }
  }

  useEffect(() => { api.adminStats().then((s) => setStats(s)).catch(() => {}); load() }, [])
  useEffect(() => { load(tab) }, [tab])

  async function act(fn, okMsg) {
    setBusy(true); setError(''); setMsg('')
    try { await fn(); setMsg(okMsg); await load() } catch (e) { setError(friendlyError(e)) } finally { setBusy(false) }
  }

  async function fundPool(e) {
    e.preventDefault()
    const amt = Number(fundAmount)
    if (!amt || amt <= 0) return setError('Escribe un monto válido en USDT.')
    await act(() => api.adminFundRewardPool(amt), `Fondo de recompensas fondeado con $${amt.toLocaleString('es', { minimumFractionDigits: 2 })} USDT.`)
    setFundAmount('')
  }

  async function saveConfig(e) {
    e.preventDefault()
    await act(() => api.adminUpdateConfig(config), 'Configuración guardada.')
  }

  const rows = Array.isArray(data) ? data : []
  const pool = tab === 'pool' && data && !Array.isArray(data) ? data : null

  return (
    <div>
      <div className="page-head"><h1>🛡️ Panel de administración</h1><p>Solo para administradores. Los pagos on-chain se hacen desde tu propia wallet; aquí solo registras el tx_hash.</p></div>
      {stats && (
        <div className="grid grid4 mb">
          <div className="card stat"><div className="label">Usuarios</div><div className="value">{stats.total_users ?? stats.users ?? '—'}</div></div>
          <div className="card stat"><div className="label">Depósitos pendientes</div><div className="value">{stats.pending_deposits ?? '—'}</div></div>
          <div className="card stat"><div className="label">Retiros pendientes</div><div className="value">{stats.pending_withdrawals ?? '—'}</div></div>
          <div className="card stat"><div className="label">Fondo de recompensas</div><div className="value gold">${Number(stats.reward_pool_usdt ?? stats.reward_pool?.balance_usdt ?? 0).toLocaleString('es', { minimumFractionDigits: 2 })}</div></div>
        </div>
      )}
      {error && <p className="notice danger">{error}</p>}
      {msg && <p className="notice ok">{msg}</p>}
      <div className="tabs">
        {TABS.map((t) => <button key={t.id} className={`tab ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>{t.label}</button>)}
      </div>

      {tab === 'pool' && (
        <div className="card mb">
          <h3>💰 Fondo de recompensas</h3>
          <p className="mt">Saldo actual: <b className="gold">${Number(pool?.balance_usdt ?? pool?.balance ?? pool?.usdt_balance ?? stats?.reward_pool_usdt ?? 0).toLocaleString('es', { minimumFractionDigits: 2 })} USDT</b></p>
          <p className="small muted">Todos los retiros se pagan desde este fondo. Si se agota, los retiros quedan en espera.</p>
          <form onSubmit={fundPool} className="row mt">
            <input type="number" min="0" step="0.01" value={fundAmount} onChange={(e) => setFundAmount(e.target.value)} placeholder="Monto en USDT" style={{ padding: '.7rem .9rem', borderRadius: 12, border: '1px solid var(--border)', background: '#0d0d22', width: 200 }} />
            <button className="btn btn-gold" type="submit" disabled={busy}>Fondear</button>
          </form>
        </div>
      )}

      {tab === 'config' && (
        <div className="card mb">
          <h3>⚙️ Configuración del juego</h3>
          <form onSubmit={saveConfig} className="mt">
            {['hck_to_usdt_rate', 'withdrawal_fee_pct', 'withdrawal_min_usdt', 'daily_bonus_hck', 'referral_bonus_hck'].map((k) => (
              <div className="field" key={k}>
                <label htmlFor={k}>{k.replaceAll('_', ' ')}</label>
                <input id={k} type="number" step="any" value={config[k] ?? ''} onChange={(e) => setConfig({ ...config, [k]: Number(e.target.value) })} />
              </div>
            ))}
            <div className="field">
              <label htmlFor="cfg-bsc">Dirección de depósito BSC (BEP-20)</label>
              <input id="cfg-bsc" value={config.deposit_address_bsc ?? config.bsc_deposit_address ?? ''} onChange={(e) => setConfig({ ...config, deposit_address_bsc: e.target.value })} placeholder="0x…" />
            </div>
            <div className="field">
              <label htmlFor="cfg-tron">Dirección de depósito TRON (TRC-20)</label>
              <input id="cfg-tron" value={config.deposit_address_tron ?? config.tron_deposit_address ?? ''} onChange={(e) => setConfig({ ...config, deposit_address_tron: e.target.value })} placeholder="T…" />
            </div>
            <button className="btn btn-primary" type="submit" disabled={busy}>Guardar configuración</button>
          </form>
          <p className="small muted mt">Los nombres exactos de los campos los define el backend (GET/PUT /api/admin/config); se envían tal cual se editan.</p>
        </div>
      )}

      {tab === 'withdrawals' && rows.length > 0 && (
        <div className="card mb">
          <h3>💸 Retiros pendientes de revisión</h3>
          <div className="table-wrap"><table>
            <thead><tr><th>Usuario</th><th>Monto</th><th>Red / Dirección</th><th>Estado</th><th>Acciones</th></tr></thead>
            <tbody>{rows.map((w, i) => (
              <tr key={w.id ?? i}>
                <td>{w.username || w.user_id || '—'}</td>
                <td>${Number(w.amount_usdt ?? 0).toLocaleString('es', { minimumFractionDigits: 2 })}</td>
                <td>{w.network || '—'} <span className="mono small">{w.address ? `${String(w.address).slice(0, 8)}…` : ''}</span></td>
                <td>{w.status || '—'}</td>
                <td>
                  <div className="row">
                    <button className="btn btn-sm" disabled={busy} onClick={() => act(() => api.adminApproveWithdrawal(w.id), 'Retiro aprobado.')}>Aprobar</button>
                    <button className="btn btn-sm btn-danger" disabled={busy} onClick={() => act(() => api.adminRejectWithdrawal(w.id), 'Retiro rechazado.')}>Rechazar</button>
                  </div>
                  <div className="row mt" style={{ marginTop: '.4rem' }}>
                    <input value={txHash[w.id] || ''} onChange={(e) => setTxHash({ ...txHash, [w.id]: e.target.value })} placeholder="tx_hash del pago" style={{ padding: '.45rem .6rem', borderRadius: 10, border: '1px solid var(--border)', background: '#0d0d22', width: 170 }} />
                    <button className="btn btn-sm btn-gold" disabled={busy || !(txHash[w.id] || '').trim()} onClick={() => act(() => api.adminMarkPaidWithdrawal(w.id, (txHash[w.id] || '').trim()), 'Retiro marcado como pagado.')}>Marcar pagado</button>
                  </div>
                </td>
              </tr>
            ))}</tbody>
          </table></div>
          <p className="small muted mt">Paga desde tu propia wallet y luego registra aquí el tx_hash. Nunca pegues claves privadas en esta app.</p>
        </div>
      )}

      {tab === 'users' && (
        <div className="card"><h3>👥 Usuarios</h3>
          {rows.length === 0 ? <p className="empty">Sin usuarios (o el endpoint aún no responde).</p> : (
            <div className="table-wrap"><table><thead><tr><th>Usuario</th><th>Nivel</th><th>HCK</th><th>USDT</th><th>Hashrate</th><th>Admin</th></tr></thead>
            <tbody>{rows.map((u, i) => (
              <tr key={u.id ?? i}><td>{u.username}</td><td>{u.level ?? '—'}</td><td>{Number(u.hck_balance ?? 0).toLocaleString('es')}</td><td>${Number(u.usdt_balance ?? 0).toLocaleString('es', { minimumFractionDigits: 2 })}</td><td>{Number(u.hashrate ?? 0).toLocaleString('es')} H/s</td><td>{u.is_admin ? 'Sí' : 'No'}</td></tr>
            ))}</tbody></table></div>
          )}
        </div>
      )}

      {tab === 'deposits' && (
        <div className="card"><h3>📥 Depósitos</h3>
          {rows.length === 0 ? <p className="empty">Sin depósitos.</p> : (
            <div className="table-wrap"><table><thead><tr><th>Usuario</th><th>Red</th><th>Monto</th><th>Tx hash</th><th>Estado</th></tr></thead>
            <tbody>{rows.map((d, i) => (
              <tr key={d.id ?? i}><td>{d.username || d.user_id || '—'}</td><td>{d.network}</td><td>${Number(d.amount_usdt ?? 0).toLocaleString('es', { minimumFractionDigits: 2 })}</td><td className="mono small">{d.tx_hash ? `${String(d.tx_hash).slice(0, 12)}…` : '—'}</td><td>{d.status}</td></tr>
            ))}</tbody></table></div>
          )}
        </div>
      )}

      {tab === 'audit' && (
        <div className="card"><h3>📜 Auditoría</h3>
          {rows.length === 0 ? <p className="empty">Sin eventos de auditoría.</p> : (
            <div className="table-wrap"><table><thead><tr><th>Fecha</th><th>Actor</th><th>Acción</th><th>Detalle</th></tr></thead>
            <tbody>{rows.map((a, i) => (
              <tr key={a.id ?? i}><td>{a.created_at ? new Date(a.created_at).toLocaleString('es') : '—'}</td><td>{a.actor || a.username || '—'}</td><td>{a.action || a.type || '—'}</td><td>{a.detail || a.description || JSON.stringify(a).slice(0, 120)}</td></tr>
            ))}</tbody></table></div>
          )}
        </div>
      )}

      {tab === 'fraud' && (
        <div className="card"><h3>🚨 Alertas de fraude</h3>
          {rows.length === 0 ? <p className="empty">Sin alertas de fraude.</p> : (
            <div className="table-wrap"><table><thead><tr><th>Fecha</th><th>Tipo</th><th>Usuario</th><th>Detalle</th><th>Severidad</th></tr></thead>
            <tbody>{rows.map((f, i) => (
              <tr key={f.id ?? i}><td>{f.created_at ? new Date(f.created_at).toLocaleString('es') : '—'}</td><td>{f.type || f.kind || '—'}</td><td>{f.username || f.user_id || '—'}</td><td>{f.detail || f.description || '—'}</td><td>{f.severity || '—'}</td></tr>
            ))}</tbody></table></div>
          )}
        </div>
      )}
    </div>
  )
}
