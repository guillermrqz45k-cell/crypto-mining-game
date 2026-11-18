import { useEffect, useState } from 'react'
import { api, friendlyError } from '../api/client.js'

const MIN_USDT = 10
const FEE_PCT = 2

function isBscAddress(a) { return /^0x[a-fA-F0-9]{40}$/.test(a) }
function isTronAddress(a) { return /^T[a-zA-Z0-9]{33}$/.test(a) }

function statusBadge(s) {
  const v = String(s || '').toLowerCase()
  if (['paid', 'pagado'].includes(v)) return <span className="badge ok">Pagado</span>
  if (['approved', 'aprobado'].includes(v)) return <span className="badge info">Aprobado</span>
  if (['rejected', 'rechazado'].includes(v)) return <span className="badge bad">Rechazado</span>
  if (['waiting_funds', 'waiting', 'en espera', 'en_espera'].includes(v)) return <span className="badge warn">En espera de fondos</span>
  return <span className="badge warn">Pendiente</span>
}

export default function Withdrawals({ user }) {
  const [list, setList] = useState([])
  const [amount, setAmount] = useState('')
  const [address, setAddress] = useState('')
  const [network, setNetwork] = useState('BSC')
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function load() {
    try { const w = await api.withdrawals(); setList(Array.isArray(w) ? w : w?.withdrawals || []) } catch (e) { setError(friendlyError(e)) }
  }
  useEffect(() => { load() }, [])

  const amt = Number(amount)
  const fee = amt > 0 ? amt * FEE_PCT / 100 : 0
  const net = amt > 0 ? amt - fee : 0
  const addrOk = address.trim() === '' || (network === 'BSC' ? isBscAddress(address.trim()) : isTronAddress(address.trim()))

  async function submit(e) {
    e.preventDefault()
    setError(''); setMsg('')
    if (!amt || amt < MIN_USDT) return setError(`El retiro mínimo es de ${MIN_USDT} USDT.`)
    if (!addrOk || !address.trim()) return setError(network === 'BSC' ? 'Dirección BSC no válida: debe empezar por 0x y tener 42 caracteres.' : 'Dirección TRON no válida: debe empezar por T y tener 34 caracteres.')
    if (user && amt > (user.usdt_balance ?? 0)) return setError('El monto supera tu saldo USDT disponible.')
    setSubmitting(true)
    try {
      await api.createWithdrawal({ amount_usdt: amt, address: address.trim(), network })
      setMsg('Retiro solicitado. Quedará en revisión y se pagará desde el fondo de recompensas.')
      setAmount(''); setAddress('')
      await load()
    } catch (err) { setError(friendlyError(err)) } finally { setSubmitting(false) }
  }

  return (
    <div>
      <div className="page-head"><h1>💸 Retiros</h1><p>Retira tus USDT a tu wallet. Saldo disponible: <b className="cyan">${(user?.usdt_balance ?? 0).toLocaleString('es', { minimumFractionDigits: 2 })} USDT</b></p></div>
      <p className="notice warn">Los retiros se pagan desde el fondo de recompensas; si el fondo no tiene saldo, tu retiro queda en espera.</p>
      {error && <p className="notice danger">{error}</p>}
      {msg && <p className="notice ok">{msg}</p>}

      <div className="card mb">
        <h2>Solicitar retiro</h2>
        <form onSubmit={submit} className="mt">
          <div className="field">
            <label htmlFor="wamount">Monto (USDT) — mínimo {MIN_USDT} USDT</label>
            <input id="wamount" type="number" min="0" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Ej. 25.00" />
          </div>
          <div className="field">
            <label htmlFor="wnetwork">Red</label>
            <select id="wnetwork" value={network} onChange={(e) => setNetwork(e.target.value)}>
              <option value="BSC">BSC (BEP-20)</option>
              <option value="TRON">TRON (TRC-20)</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="waddr">Dirección de destino ({network})</label>
            <input id="waddr" value={address} onChange={(e) => setAddress(e.target.value)} placeholder={network === 'BSC' ? '0x…' : 'T…'} />
            {address && !addrOk && <span className="hint" style={{ color: 'var(--red)' }}>Formato de dirección no válido para {network}.</span>}
          </div>
          {amt > 0 && (
            <p className="small">Comisión {FEE_PCT}%: <b>${fee.toLocaleString('es', { minimumFractionDigits: 2 })}</b> · Recibirás aprox.: <b className="green">${net.toLocaleString('es', { minimumFractionDigits: 2 })} USDT</b></p>
          )}
          <button className="btn btn-primary mt" type="submit" disabled={submitting}>{submitting ? 'Enviando…' : 'Solicitar retiro'}</button>
        </form>
      </div>

      <div className="card">
        <h2>Historial de retiros</h2>
        {list.length === 0 ? <p className="empty">Aún no has solicitado retiros.</p> : (
          <div className="table-wrap"><table>
            <thead><tr><th>Fecha</th><th>Monto</th><th>Red</th><th>Dirección</th><th>Estado</th><th>Tx hash</th></tr></thead>
            <tbody>{list.map((w, i) => (
              <tr key={w.id ?? i}>
                <td>{w.created_at ? new Date(w.created_at).toLocaleString('es') : '—'}</td>
                <td>${Number(w.amount_usdt ?? 0).toLocaleString('es', { minimumFractionDigits: 2 })}</td>
                <td>{w.network || '—'}</td>
                <td className="mono small">{w.address ? `${String(w.address).slice(0, 8)}…${String(w.address).slice(-4)}` : '—'}</td>
                <td>{statusBadge(w.status)}</td>
                <td className="mono small">{w.tx_hash ? `${String(w.tx_hash).slice(0, 10)}…` : '—'}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </div>
    </div>
  )
}
