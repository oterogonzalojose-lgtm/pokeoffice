import { useState, useEffect } from 'react'

const API = import.meta.env.VITE_API_URL ?? ''

function formatDate(str) {
  if (!str) return ''
  const d = new Date(str.replace(' ', 'T') + 'Z')
  return isNaN(d) ? str : d.toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function ConversationItem({ item }) {
  const [open, setOpen] = useState(false)
  return (
    <div
      className="border border-[#1e1e3a] rounded p-2 cursor-pointer hover:border-[#3a3a6a] transition-colors"
      onClick={() => setOpen(o => !o)}
    >
      <div className="flex items-start gap-1.5">
        <span className="text-[10px] font-mono text-[#4A90D9] shrink-0 mt-0.5">Jefe</span>
        <p className="text-[11px] font-mono text-gray-200 leading-snug line-clamp-2 flex-1">
          {item.user_message}
        </p>
        <span className="text-[9px] text-gray-600 font-mono shrink-0 mt-0.5">
          {open ? '▲' : '▼'}
        </span>
      </div>
      {open && (
        <div className="mt-2 pt-2 border-t border-[#1e1e3a]">
          <div className="flex items-start gap-1.5 mb-1">
            <span className="text-[10px] font-mono text-[#27AE60] shrink-0">VP</span>
            <p className="text-[11px] font-mono text-gray-400 leading-snug whitespace-pre-wrap flex-1">
              {item.vp_response}
            </p>
          </div>
          <p className="text-[9px] font-mono text-gray-600 text-right mt-1">
            {formatDate(item.created_at)}
          </p>
        </div>
      )}
    </div>
  )
}

export default function ConversationHistory() {
  const [history, setHistory]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)

  useEffect(() => {
    fetch(`${API}/history?limit=50`)
      .then(r => r.json())
      .then(data => { setHistory(data); setLoading(false) })
      .catch(() => { setError('No se pudo cargar el historial'); setLoading(false) })
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <span className="text-[11px] font-mono text-gray-500 animate-pulse">Cargando...</span>
    </div>
  )

  if (error) return (
    <div className="flex items-center justify-center h-full">
      <span className="text-[11px] font-mono text-red-500">{error}</span>
    </div>
  )

  if (!history.length) return (
    <div className="flex items-center justify-center h-full">
      <span className="text-[11px] font-mono text-gray-600">Sin conversaciones aún</span>
    </div>
  )

  return (
    <div className="flex flex-col gap-1.5 p-2 overflow-y-auto h-full">
      {history.map(item => (
        <ConversationItem key={item.id} item={item} />
      ))}
    </div>
  )
}
