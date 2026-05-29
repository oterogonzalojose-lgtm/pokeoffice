export const BASE      = import.meta.env.VITE_API_URL ?? ''
export const TOKEN_KEY = 'user_token'

export const getToken   = () => localStorage.getItem(TOKEN_KEY)
export const setToken   = t  => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

export async function apiFetch(path, options = {}) {
  const token = getToken()
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (res.status === 401) {
    clearToken()
    window.location.reload()
  }
  return res
}

export function getWsUrl() {
  const token = getToken()
  const base  = import.meta.env.VITE_WS_URL
    ?? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`
  return token ? `${base}?token=${encodeURIComponent(token)}` : base
}
