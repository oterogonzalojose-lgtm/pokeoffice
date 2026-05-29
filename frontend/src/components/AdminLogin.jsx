import { useState } from 'react'

const API = import.meta.env.VITE_API_URL ?? ''

export default function AdminLogin({ onLogin }) {
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/api/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      if (!res.ok) { setError('Contraseña incorrecta'); setLoading(false); return }
      const { token } = await res.json()
      localStorage.setItem('admin_token', token)
      onLogin(token)
    } catch {
      setError('Error de conexión')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a18] flex items-center justify-center">
      <div className="bg-[#07070f] border border-[#1e1e3a] rounded-lg p-8 w-80">
        <div className="text-center mb-6">
          <span className="text-4xl">🏢</span>
          <h1 className="text-white font-mono font-bold text-lg mt-2">Pokeoffice Admin</h1>
          <p className="text-gray-600 font-mono text-xs mt-1">Acceso restringido</p>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Contraseña"
            className="bg-[#0a0a18] border border-[#1e1e3a] rounded px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-[#4A90D9]"
            autoFocus
          />
          {error && <p className="text-red-400 font-mono text-xs">{error}</p>}
          <button
            type="submit"
            disabled={loading || !password}
            className="bg-[#4A90D9] hover:bg-[#3a7bc8] disabled:opacity-40 text-white font-mono text-sm py-2 rounded transition-colors"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}
