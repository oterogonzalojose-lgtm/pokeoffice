import { useState } from 'react'
import { BASE, setToken } from '../utils/api'

// ── Fases ─────────────────────────────────────────────────────────────────────
// 'inicio'    → email + dos opciones
// 'solicitud' → email + nombre → solicitar acceso
// 'codigo'    → email + código 6 dígitos → verificar
// 'enviado'   → confirmación de solicitud enviada

export default function LoginScreen({ onLogin }) {
  const [fase,     setFase]     = useState('inicio')
  const [email,    setEmail]    = useState('')
  const [nombre,   setNombre]   = useState('')
  const [codigo,   setCodigo]   = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  // ── Solicitar acceso ──────────────────────────────────────────────────────

  async function handleSolicitar(e) {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      await fetch(`${BASE}/auth/solicitar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, nombre }),
      })
      setFase('enviado')
    } catch {
      setError('Error de conexión. Intentá de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  // ── Verificar código ──────────────────────────────────────────────────────

  async function handleVerificar(e) {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const res  = await fetch(`${BASE}/auth/verificar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, codigo }),
      })
      const json = await res.json()
      if (!res.ok) { setError(json.detail || 'Código incorrecto'); setLoading(false); return }
      setToken(json.token)
      onLogin(json.user)
    } catch {
      setError('Error de conexión. Intentá de nuevo.')
      setLoading(false)
    }
  }

  // ── Renders ───────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#0a0a18] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-[#07070f] border border-[#1e1e3a] rounded-xl p-8 shadow-2xl">

        {/* Logo */}
        <div className="text-center mb-8">
          <span className="text-5xl">🏢</span>
          <h1 className="text-white font-mono font-bold text-xl mt-3 tracking-widest uppercase">
            Pokeoffice
          </h1>
          <p className="text-gray-600 font-mono text-xs mt-1">Tu mini oficina con IA</p>
        </div>

        {/* ── Fase: inicio ───────────────────────────────────────────────── */}
        {fase === 'inicio' && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-mono text-gray-400">Tu email</label>
              <input
                type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder="nombre@empresa.com" autoFocus
                className="bg-[#0a0a18] border border-[#1e1e3a] focus:border-[#4A90D9]
                           rounded px-3 py-2.5 text-white font-mono text-sm outline-none transition-colors"
              />
            </div>
            <div className="flex flex-col gap-2 mt-2">
              <button
                disabled={!email || !email.includes('@')}
                onClick={() => { setError(''); setFase('codigo') }}
                className="w-full bg-[#4A90D9] hover:bg-[#3a7bc8] disabled:opacity-40
                           text-white font-mono text-sm py-2.5 rounded transition-colors font-bold">
                Ya tengo un código →
              </button>
              <button
                disabled={!email || !email.includes('@')}
                onClick={() => { setError(''); setFase('solicitud') }}
                className="w-full bg-transparent border border-[#1e1e3a] hover:border-[#3a3a6a]
                           disabled:opacity-40 text-gray-400 hover:text-white font-mono text-sm
                           py-2.5 rounded transition-colors">
                Solicitar acceso
              </button>
            </div>
          </div>
        )}

        {/* ── Fase: solicitud ─────────────────────────────────────────────── */}
        {fase === 'solicitud' && (
          <form onSubmit={handleSolicitar} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-mono text-gray-500">Email</label>
              <p className="text-sm font-mono text-gray-300">{email}</p>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-mono text-gray-400">Tu nombre</label>
              <input
                type="text" value={nombre} onChange={e => setNombre(e.target.value)}
                placeholder="Ej: Martín García" autoFocus required
                className="bg-[#0a0a18] border border-[#1e1e3a] focus:border-[#4A90D9]
                           rounded px-3 py-2.5 text-white font-mono text-sm outline-none transition-colors"
              />
            </div>
            {error && <p className="text-red-400 font-mono text-xs">{error}</p>}
            <div className="flex gap-2 mt-1">
              <button type="button" onClick={() => setFase('inicio')}
                className="flex-1 border border-[#1e1e3a] text-gray-500 hover:text-gray-300
                           font-mono text-sm py-2.5 rounded transition-colors">
                ← Volver
              </button>
              <button type="submit" disabled={loading || !nombre.trim()}
                className="flex-1 bg-[#4A90D9] hover:bg-[#3a7bc8] disabled:opacity-40
                           text-white font-mono text-sm py-2.5 rounded transition-colors font-bold">
                {loading ? 'Enviando...' : 'Solicitar'}
              </button>
            </div>
          </form>
        )}

        {/* ── Fase: código ────────────────────────────────────────────────── */}
        {fase === 'codigo' && (
          <form onSubmit={handleVerificar} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-mono text-gray-500">Email</label>
              <p className="text-sm font-mono text-gray-300">{email}</p>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-mono text-gray-400">Código de acceso (6 dígitos)</label>
              <input
                type="text" inputMode="numeric" maxLength={6}
                value={codigo} onChange={e => setCodigo(e.target.value.replace(/\D/g, ''))}
                placeholder="_ _ _ _ _ _" autoFocus required
                className="bg-[#0a0a18] border border-[#1e1e3a] focus:border-[#4A90D9]
                           rounded px-3 py-2.5 text-white font-mono text-xl outline-none
                           transition-colors text-center tracking-[0.5em]"
              />
              <p className="text-[10px] font-mono text-gray-600">
                El código te lo envía el equipo de Pokeoffice
              </p>
            </div>
            {error && <p className="text-red-400 font-mono text-xs">{error}</p>}
            <div className="flex gap-2 mt-1">
              <button type="button" onClick={() => { setFase('inicio'); setCodigo(''); setError('') }}
                className="flex-1 border border-[#1e1e3a] text-gray-500 hover:text-gray-300
                           font-mono text-sm py-2.5 rounded transition-colors">
                ← Volver
              </button>
              <button type="submit" disabled={loading || codigo.length !== 6}
                className="flex-1 bg-[#4A90D9] hover:bg-[#3a7bc8] disabled:opacity-40
                           text-white font-mono text-sm py-2.5 rounded transition-colors font-bold">
                {loading ? 'Verificando...' : 'Ingresar →'}
              </button>
            </div>
          </form>
        )}

        {/* ── Fase: enviado ────────────────────────────────────────────────── */}
        {fase === 'enviado' && (
          <div className="flex flex-col items-center gap-4 text-center">
            <span className="text-4xl">✉️</span>
            <div>
              <p className="text-white font-mono font-bold">¡Solicitud recibida!</p>
              <p className="text-gray-500 font-mono text-sm mt-2">
                El equipo de Pokeoffice revisará tu solicitud y te enviará
                tu código de acceso a <span className="text-gray-300">{email}</span>.
              </p>
            </div>
            <button onClick={() => { setFase('codigo'); setError('') }}
              className="text-[#4A90D9] hover:text-[#3a7bc8] font-mono text-sm transition-colors">
              Ya tengo el código →
            </button>
          </div>
        )}

      </div>
    </div>
  )
}
