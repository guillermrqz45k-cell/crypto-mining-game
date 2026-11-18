import { useEffect, useState } from 'react'
import { api, friendlyError } from '../api/client.js'
import WalletConnectButton from '../components/WalletConnectButton.jsx'

function statusBadge(s) {
  const v = String(s || '').toLowerCase()
  if (['verified', 'verificado', 'approved', 'aprobado', 'completed', 'completado'].includes(v)) return <span className="badge ok">Verificado</span>
  if (['rejected', 'rechazado'].includes(v)) return <span className="badge bad">Rechazado</span>
  return <span className="badge warn">Pendiente</span>
}

export default function Wallet({ user }) {
  const [wallet, setWallet] = useState(null)
  const [deposits, setDeposits] = useState([])
  const [txs, setTxs] = useState([])
  const [network, setNetwork] = useState('BSC')
  const [txHash, setTxHash] = useState('')
  const [amount, setAmount] = useState('')
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [copied, setCopied] = useState('')

  async function load() {
    setLoading(true)
    try {
      const w = await api.wallet()
      setWallet(w)
    } catch (e) { setError(friendlyError(e)) }
    try { const d = await api.deposits(); setDeposits(Array.isArray(d) ? d : d?.deposits || []) } catch { setDeposits([]) }
    try { const t = await api.transactions(); setTxs(Array.isArray(t) ? t : t?.transactions || []) } catch { setTxs([]) }
    setLoading(false)
  }
  useEffect(() => { load() }, [])

  const addrs = wallet?.deposit_addresses || {}
  const addr = network === 'BSC' ? addrs.bsc : addrs.tron
  const configured = !!(addr && String(addr).trim())
  const rate = wallet?.hck_to_usdt_rate ?? null

  function copy(text, key) {
    if (!text) return
    navigator.clipboard?.writeText(text).then(() => { setCopied(key); setTimeout(() => setCopied(''), 2000) }).catch(() => {})
  }

  async function submitDeposit(e) {
    e.preventDefault()
    setError(''); setMsg('')
    if (!configured) return setError('Los depósitos están desactivados: el administrador aún no configuró las direcciones.')
    if (!txHash.trim()) return setError('Escribe el hash de la transacción (tx_hash).')
    const amt = Number(amount)
    if (!amt || amt <= 0) return setError('Escribe un monto válido en USDT (mayor que 0).')
    setSubmitting(true)
    try {
      await api.registerDeposit({ tx_hash: txHash.trim(), network, amount_usdt: amt })
      setMsg('Depósito registrado. La verificación es on-chain y puede tardar unos minutos; verás el estado en el historial.')
      setTxHash(''); setAmount('')
      await load()
    } catch (err) { setError(friendlyError(err)) } finally { setSubmitting(false) }
  }

  return (
    <div>
      <div className="page-head"><h1>👛 Billetera</h1><p>Deposita USDT, convierte HCK y sigue todos tus movimientos.</p></div>
      {error && <p className="notice danger">{error}</p>}
      {msg && <p className="notice ok">{msg}</p>}
      {loading && <p className="muted">Cargando billetera…</p>}

      <div className="grid grid3 mb">
        <div className="card stat"><div className="label">Saldo USDT</div><div className="value cyan">${(wallet?.usdt_balance ?? user?.usdt_balance ?? 0).toLocaleString('es', { minimumFractionDigits: 2 })}</div></div>
        <div className="card stat"><div className="label">Saldo HCK</div><div className="value gold">🪙 {(wallet?.hck_balance ?? user?.hck_balance ?? 0).toLocaleString('es')}</div></div>
        <div className="card stat"><div className="label">Tasa HCK → USDT</div><div className="value">{rate ? `${Number(rate).toLocaleString('es')} HCK = 1 USDT` : '—'}</div><div className="sub">La fija el administrador</div></div>
      </div>

      <div className="card mb">
        <h3>🔗 Conectar billetera</h3>
        <p className="small muted mb">Conecta tu wallet para futuras funciones (pagos y retiros on-chain). Conectar no mueve fondos.</p>
        <WalletConnectButton />
      </div>

      <div className="card mb">
        <h2>💰 Depósito de USDT</h2>
        <div className="tabs mt">
          <button className={`tab ${network === 'BSC' ? 'active' : ''}`} onClick={() => setNetwork('BSC')}>BSC (BEP-20)</button>
          <button className={`tab ${network === 'TRON' ? 'active' : ''}`} onClick={() => setNetwork('TRON')}>TRON (TRC-20)</button>
        </div>
        {configured ? (
          <div>
            <p className="small muted">Envía USDT ({network === 'BSC' ? 'BEP-20' : 'TRC-20'}) a esta dirección del proyecto:</p>
            <div className="code-box mt">{addr}</div>
            <button className="btn btn-sm mt" onClick={() => copy(addr, 'addr')}>{copied === 'addr' ? '✓ Copiada' : '📋 Copiar dirección'}</button>
            <p className="small muted mt">⚠️ Envía solo USDT por la red {network}. Enviar otra moneda u otra red puede perder los fondos.</p>
          </div>
        ) : (
          <p className="notice warn">Las direcciones de depósito aún no están configuradas por el administrador — los depósitos están desactivados.</p>
        )}
        <form onSubmit={submitDeposit} className="mt">
          <div className="field">
            <label htmlFor="txhash">Hash de la transacción (tx_hash)</label>
            <input id="txhash" value={txHash} onChange={(e) => setTxHash(e.target.value)} placeholder="0x…" disabled={!configured} />
          </div>
          <div className="field">
            <label htmlFor="depamount">Monto (USDT)</label>
            <input id="depamount" type="number" min="0" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Ej. 25.00" disabled={!configured} />
            <span className="hint">Después de enviar el USDT, registra aquí el tx_hash y el monto. La verificación es on-chain y puede tardar unos minutos.</span>
          </div>
          <button className="btn btn-primary" type="submit" disabled={!configured || submitting}>{submitting ? 'Registrando…' : 'Registrar depósito'}</button>
        </form>
      </div>

      <div className="card mb">
        <h2>📥 Historial de depósitos</h2>
        {deposits.length === 0 ? <p className="empty">Aún no tienes depósitos registrados.</p> : (
          <div className="table-wrap"><table>
            <thead><tr><th>Fecha</th><th>Red</th><th>Monto</th><th>Tx hash</th><th>Estado</th></tr></thead>
            <tbody>{deposits.map((d, i) => (
              <tr key={d.id ?? i}>
                <td>{d.created_at ? new Date(d.created_at).toLocaleString('es') : '—'}</td>
                <td>{d.network || '—'}</td>
                <td>${Number(d.amount_usdt ?? 0).toLocaleString('es', { minimumFractionDigits: 2 })}</td>
                <td className="mono small">{d.tx_hash ? `${String(d.tx_hash).slice(0, 10)}…${String(d.tx_hash).slice(-6)}` : '—'}</td>
                <td>{statusBadge(d.status)}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </div>

      <div className="card">
        <h2>📜 Historial de transacciones</h2>
        {txs.length === 0 ? <p className="empty">Aún no hay movimientos.</p> : (
          <div className="table-wrap"><table>
            <thead><tr><th>Fecha</th><th>Tipo</th><th>Monto</th><th>Detalle</th></tr></thead>
            <tbody>{txs.map((t, i) => (
              <tr key={t.id ?? i}>
                <td>{t.created_at ? new Date(t.created_at).toLocaleString('es') : '—'}</td>
                <td>{t.type || t.kind || '—'}</td>
                <td>{t.amount_hck ? `${Number(t.amount_hck).toLocaleString('es')} HCK` : t.amount_usdt ? `$${Number(t.amount_usdt).toLocaleString('es', { minimumFractionDigits: 2 })}` : '—'}</td>
                <td>{t.description || t.note || '—'}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </div>
    </div>
  )
}
