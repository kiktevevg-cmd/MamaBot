// In Telegram Mini App the page and API share the same HTTPS origin (tunnel).
const API_URL = import.meta.env.VITE_API_URL || ''

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export function getUserId() {
  const tg = window.Telegram?.WebApp
  const fromTg = tg?.initDataUnsafe?.user?.id
  if (fromTg) return fromTg
  return parseInt(localStorage.getItem('dev_user_id') || '0', 10)
}

export const api = {
  getSettings: (userId) => request(`/api/settings/${userId}`),
  updateSettings: (data) =>
    request('/api/settings/update', { method: 'POST', body: JSON.stringify(data) }),
  getFacts: (userId) => request(`/api/memory/facts/${userId}`),
  clearMemory: (data) =>
    request('/api/memory/clear', { method: 'POST', body: JSON.stringify(data) }),
  deleteFact: (data) =>
    request('/api/memory/delete', { method: 'POST', body: JSON.stringify(data) }),
  activateDnd: (data) =>
    request('/api/dnd/activate', { method: 'POST', body: JSON.stringify(data) }),
}
