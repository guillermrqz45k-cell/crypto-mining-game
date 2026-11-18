// Cliente HTTP del frontend — fetch + token Bearer en localStorage.
// La URL de la API se lee de VITE_API_URL (por defecto http://localhost:8000).
const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export const apiUrl = API_URL
const TOKEN_KEY = 'cmg_token'

export function getToken() { return localStorage.getItem(TOKEN_KEY) }
export function setToken(t) { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY) }
export function isLoggedIn() { return !!getToken() }

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }
  let res
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch (e) {
    // Backend caído o sin red: error elegante, nunca rompe la UI.
    throw new Error('No se pudo conectar con el servidor. Comprueba que el backend esté en marcha.')
  }
  let data = null
  try { data = await res.json() } catch { data = null }
  if (!res.ok) {
    const msg = (data && (data.detail || data.message || data.error)) || `Error ${res.status}`
    const err = new Error(typeof msg === 'string' ? msg : 'Error del servidor')
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

export const api = {
  health: () => request('/health', { auth: false }),
  register: (payload) => request('/api/auth/register', { method: 'POST', body: payload, auth: false }),
  login: (payload) => request('/api/auth/login', { method: 'POST', body: payload, auth: false }),
  me: () => request('/api/me'),
  miningStatus: () => request('/api/mining/status'),
  miningStart: () => request('/api/mining/start', { method: 'POST' }),
  miningStop: () => request('/api/mining/stop', { method: 'POST' }),
  miningCollect: () => request('/api/mining/collect', { method: 'POST' }),
  machines: () => request('/api/machines'),
  myMachines: () => request('/api/machines/mine'),
  buyMachine: (machine_id) => request('/api/machines/buy', { method: 'POST', body: { machine_id } }),
  upgradeMachine: (owned_machine_id) => request('/api/machines/upgrade', { method: 'POST', body: { owned_machine_id } }),
  missions: () => request('/api/missions'),
  claimMission: (mission_id) => request('/api/missions/claim', { method: 'POST', body: { mission_id } }),
  claimDailyBonus: () => request('/api/daily-bonus/claim', { method: 'POST' }),
  wallet: () => request('/api/wallet'),
  registerDeposit: (payload) => request('/api/wallet/deposits', { method: 'POST', body: payload }),
  deposits: () => request('/api/wallet/deposits'),
  transactions: () => request('/api/wallet/transactions'),
  createWithdrawal: (payload) => request('/api/withdrawals', { method: 'POST', body: payload }),
  withdrawals: () => request('/api/withdrawals'),
  referrals: () => request('/api/referrals'),
  leaderboard: () => request('/api/leaderboard'),
  stats: () => request('/api/stats'),
  // Admin
  adminStats: () => request('/api/admin/stats'),
  adminUsers: () => request('/api/admin/users'),
  adminDeposits: () => request('/api/admin/deposits'),
  adminWithdrawals: () => request('/api/admin/withdrawals'),
  adminApproveWithdrawal: (id) => request(`/api/admin/withdrawals/${id}/approve`, { method: 'POST' }),
  adminRejectWithdrawal: (id) => request(`/api/admin/withdrawals/${id}/reject`, { method: 'POST' }),
  adminMarkPaidWithdrawal: (id, tx_hash) => request(`/api/admin/withdrawals/${id}/mark-paid`, { method: 'POST', body: { tx_hash } }),
  adminRewardPool: () => request('/api/admin/reward-pool'),
  adminFundRewardPool: (amount_usdt) => request('/api/admin/reward-pool/fund', { method: 'POST', body: { amount_usdt } }),
  adminConfig: () => request('/api/admin/config'),
  adminUpdateConfig: (cfg) => request('/api/admin/config', { method: 'PUT', body: cfg }),
  adminAudit: () => request('/api/admin/audit'),
  adminFraudAlerts: () => request('/api/admin/fraud-alerts'),
}

export function friendlyError(err) {
  if (!err) return 'Error desconocido'
  return err.message || 'Error desconocido'
}
