import { useState, useEffect } from 'react'

// ── Tipos de post-it con paleta hiperrealista ─────────────────────────────────
export const POST_IT_TYPES = {
  recordatorio: {
    label: 'Recordatorio',
    icon:  '📌',
    bg:    'linear-gradient(160deg, #fff9c4 0%, #fff176 60%, #fdd835 100%)',
    strip: '#f9a825',
    text:  '#3e2723',
    glow:  'rgba(253,216,53,0.4)',
  },
  urgente: {
    label: 'Urgente',
    icon:  '🚨',
    bg:    'linear-gradient(160deg, #ffd7d7 0%, #ffb3b3 60%, #ef9a9a 100%)',
    strip: '#c62828',
    text:  '#b71c1c',
    glow:  'rgba(239,154,154,0.4)',
  },
  cliente: {
    label: 'Cliente',
    icon:  '👤',
    bg:    'linear-gradient(160deg, #f3e5f5 0%, #e1bee7 60%, #ce93d8 100%)',
    strip: '#7b1fa2',
    text:  '#4a148c',
    glow:  'rgba(206,147,216,0.4)',
  },
  financiero: {
    label: 'Financiero',
    icon:  '💰',
    bg:    'linear-gradient(160deg, #e3f2fd 0%, #bbdefb 60%, #90caf9 100%)',
    strip: '#1565c0',
    text:  '#0d47a1',
    glow:  'rgba(144,202,249,0.4)',
  },
  stock: {
    label: 'Stock / Compra',
    icon:  '📦',
    bg:    'linear-gradient(160deg, #e8f5e9 0%, #c8e6c9 60%, #a5d6a7 100%)',
    strip: '#2e7d32',
    text:  '#1b5e20',
    glow:  'rgba(165,214,167,0.4)',
  },
  tarea: {
    label: 'Tarea',
    icon:  '✅',
    bg:    'linear-gradient(160deg, #fff3e0 0%, #ffe0b2 60%, #ffcc80 100%)',
    strip: '#e65100',
    text:  '#bf360c',
    glow:  'rgba(255,204,128,0.4)',
  },
}

// ── Rotaciones pseudo-aleatorias por índice ───────────────────────────────────
const ROTATIONS = [-2.8, 1.4, -1.1, 2.3, -0.7, 1.9, -2.2, 0.8, -1.6, 2.5]

// ── Post-it individual ────────────────────────────────────────────────────────
function PostIt({ item, index, onDelete, onToggle }) {
  const theme = POST_IT_TYPES[item.tipo] ?? POST_IT_TYPES.recordatorio
  const rot   = ROTATIONS[index % ROTATIONS.length]
  const [hovered, setHovered] = useState(false)

  return (
    <div
      style={{
        position:   'relative',
        transform:  `rotate(${hovered ? rot * 0.4 : rot}deg) translateY(${hovered ? -4 : 0}px)`,
        transition: 'transform 0.18s ease, box-shadow 0.18s ease',
        boxShadow:  hovered
          ? `4px 8px 20px rgba(0,0,0,0.35), 0 0 14px ${theme.glow}`
          : `3px 5px 12px rgba(0,0,0,0.28), 1px 2px 4px rgba(0,0,0,0.14)`,
        borderRadius: '2px',
        cursor: 'default',
        minWidth: 120,
        maxWidth: 160,
        flexShrink: 0,
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Paper background */}
      <div style={{
        background:   theme.bg,
        borderRadius: '2px',
        overflow:     'hidden',
        opacity:      item.completado ? 0.55 : 1,
      }}>
        {/* Adhesive strip (top) */}
        <div style={{
          background:   theme.strip,
          height:       10,
          opacity:      0.85,
          position:     'relative',
        }}>
          {/* Tape shine */}
          <div style={{
            position:   'absolute', top: 2, left: '15%',
            width: '70%', height: 3,
            background: 'rgba(255,255,255,0.28)',
            borderRadius: 2,
          }} />
        </div>

        {/* Content */}
        <div style={{ padding: '8px 10px 10px' }}>
          {/* Type badge */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4,
            marginBottom: 5,
          }}>
            <span style={{ fontSize: 11 }}>{theme.icon}</span>
            <span style={{
              fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
              letterSpacing: '0.06em', color: theme.strip, fontFamily: 'monospace',
            }}>
              {theme.label}
            </span>
          </div>

          {/* Text */}
          <p
            style={{
              fontSize: 11.5, lineHeight: 1.45,
              color:    theme.text,
              fontFamily: '"Segoe UI", system-ui, sans-serif',
              fontWeight: 500,
              textDecoration: item.completado ? 'line-through' : 'none',
              margin: 0, wordBreak: 'break-word',
              whiteSpace: 'pre-wrap',
            }}
          >
            {item.texto}
          </p>

          {/* Timestamp */}
          {item.fecha && (
            <p style={{
              fontSize: 9, color: theme.strip, opacity: 0.7,
              marginTop: 6, marginBottom: 0, fontFamily: 'monospace',
            }}>
              {item.fecha}
            </p>
          )}
        </div>

        {/* Fold corner (bottom-right) */}
        <div style={{
          position: 'absolute', bottom: 0, right: 0,
          width: 0, height: 0,
          borderStyle: 'solid',
          borderWidth: '0 0 16px 16px',
          borderColor: `transparent transparent rgba(0,0,0,0.18) transparent`,
          filter: 'drop-shadow(-1px -1px 1px rgba(0,0,0,0.1))',
        }} />
      </div>

      {/* Action buttons — aparecen al hover */}
      {hovered && (
        <div style={{
          position: 'absolute', top: -8, right: -8,
          display: 'flex', gap: 3, zIndex: 10,
        }}>
          <button
            onClick={() => onToggle(item.id)}
            title={item.completado ? 'Desmarcar' : 'Completar'}
            style={{
              width: 20, height: 20, borderRadius: '50%',
              background: item.completado ? '#bdbdbd' : '#4caf50',
              border: 'none', cursor: 'pointer', fontSize: 10,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
              color: 'white', fontWeight: 'bold',
            }}
          >✓</button>
          <button
            onClick={() => onDelete(item.id)}
            title="Eliminar"
            style={{
              width: 20, height: 20, borderRadius: '50%',
              background: '#f44336',
              border: 'none', cursor: 'pointer', fontSize: 11,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
              color: 'white', fontWeight: 'bold',
            }}
          >×</button>
        </div>
      )}
    </div>
  )
}

// ── Formulario de nuevo post-it ───────────────────────────────────────────────
function AddPostItForm({ onAdd, onClose }) {
  const [texto, setTexto] = useState('')
  const [tipo,  setTipo]  = useState('recordatorio')

  function handleSubmit(e) {
    e.preventDefault()
    if (!texto.trim()) return
    onAdd({ texto: texto.trim(), tipo })
    setTexto('')
    onClose()
  }

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        background:   POST_IT_TYPES[tipo].bg,
        boxShadow:    '3px 5px 14px rgba(0,0,0,0.3)',
        borderRadius: '2px',
        overflow:     'hidden',
        minWidth: 150,
      }}
    >
      {/* Strip */}
      <div style={{ background: POST_IT_TYPES[tipo].strip, height: 10 }} />

      <div style={{ padding: '8px 10px 10px' }}>
        {/* Tipo selector */}
        <select
          value={tipo}
          onChange={e => setTipo(e.target.value)}
          style={{
            width: '100%', fontSize: 10, fontFamily: 'monospace',
            background: 'transparent', border: 'none',
            borderBottom: `1px solid ${POST_IT_TYPES[tipo].strip}`,
            color: POST_IT_TYPES[tipo].strip, fontWeight: 700,
            marginBottom: 6, cursor: 'pointer', outline: 'none',
            paddingBottom: 3,
          }}
        >
          {Object.entries(POST_IT_TYPES).map(([key, t]) => (
            <option key={key} value={key}>{t.icon} {t.label}</option>
          ))}
        </select>

        {/* Texto */}
        <textarea
          autoFocus
          value={texto}
          onChange={e => setTexto(e.target.value)}
          placeholder="Escribí la nota..."
          rows={3}
          style={{
            width: '100%', resize: 'none', border: 'none', outline: 'none',
            background: 'transparent', fontSize: 11.5, lineHeight: 1.45,
            color: POST_IT_TYPES[tipo].text, fontFamily: '"Segoe UI", system-ui, sans-serif',
            fontWeight: 500,
          }}
          onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleSubmit(e) }}
        />

        <div style={{ display: 'flex', gap: 4, marginTop: 6, justifyContent: 'flex-end' }}>
          <button
            type="button" onClick={onClose}
            style={{
              fontSize: 9, padding: '2px 7px', cursor: 'pointer',
              background: 'rgba(0,0,0,0.12)', border: 'none', borderRadius: 2,
              color: POST_IT_TYPES[tipo].text, fontFamily: 'monospace',
            }}
          >Cancelar</button>
          <button
            type="submit"
            style={{
              fontSize: 9, padding: '2px 7px', cursor: 'pointer',
              background: POST_IT_TYPES[tipo].strip, border: 'none', borderRadius: 2,
              color: 'white', fontFamily: 'monospace', fontWeight: 700,
            }}
          >Pegar ↵</button>
        </div>
      </div>
    </form>
  )
}

// ── Tablero principal ─────────────────────────────────────────────────────────
const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function PostItBoard({ newReminder }) {
  const [postIts,    setPostIts]    = useState([])
  const [showForm,   setShowForm]   = useState(false)
  const [filterTipo, setFilterTipo] = useState('todos')

  // Cargar desde backend
  useEffect(() => {
    fetch(`${API}/recordatorios`)
      .then(r => r.json())
      .then(data => setPostIts(data))
      .catch(() => {})
  }, [])

  // Recibir recordatorio automático del scheduler via prop
  useEffect(() => {
    if (!newReminder) return
    setPostIts(prev => {
      if (prev.find(p => p.id === newReminder.id)) return prev
      return [newReminder, ...prev]
    })
  }, [newReminder])

  async function handleAdd({ texto, tipo }) {
    const fecha = new Date().toLocaleDateString('es-AR', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' })
    const nuevo = { texto, tipo, fecha, completado: false }
    try {
      const res  = await fetch(`${API}/recordatorios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nuevo),
      })
      const saved = await res.json()
      setPostIts(prev => [saved, ...prev])
    } catch {
      // fallback: agregar localmente con id temporal
      setPostIts(prev => [{ ...nuevo, id: Date.now() }, ...prev])
    }
  }

  async function handleDelete(id) {
    setPostIts(prev => prev.filter(p => p.id !== id))
    try { await fetch(`${API}/recordatorios/${id}`, { method: 'DELETE' }) } catch {}
  }

  async function handleToggle(id) {
    setPostIts(prev => prev.map(p =>
      p.id === id ? { ...p, completado: !p.completado } : p
    ))
    try {
      await fetch(`${API}/recordatorios/${id}/toggle`, { method: 'PATCH' })
    } catch {}
  }

  const filtered = filterTipo === 'todos'
    ? postIts
    : postIts.filter(p => p.tipo === filterTipo)

  const pendientes  = postIts.filter(p => !p.completado).length
  const completados = postIts.filter(p =>  p.completado).length

  return (
    <div className="flex flex-col gap-2 shrink-0" style={{ width: 188 }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[10px] uppercase font-bold text-gray-500 font-mono tracking-widest">
            Post-its
          </h2>
          <p className="text-[9px] font-mono text-gray-600">
            {pendientes} pendiente{pendientes !== 1 ? 's' : ''} · {completados} listo{completados !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => setShowForm(f => !f)}
          title="Nuevo post-it"
          className="w-6 h-6 flex items-center justify-center rounded text-sm font-bold
                     bg-[#1e1e3a] border border-[#3a3a6a] text-gray-300
                     hover:bg-[#2a2a4a] hover:text-white transition-colors"
        >+</button>
      </div>

      {/* Filtro por tipo */}
      <div className="flex flex-wrap gap-1">
        <button
          onClick={() => setFilterTipo('todos')}
          className={`text-[9px] font-mono px-1.5 py-0.5 rounded transition-colors
            ${filterTipo === 'todos' ? 'bg-[#3a3a6a] text-white' : 'text-gray-500 hover:text-gray-300'}`}
        >Todos</button>
        {Object.entries(POST_IT_TYPES).map(([key, t]) => (
          <button
            key={key}
            onClick={() => setFilterTipo(key === filterTipo ? 'todos' : key)}
            className={`text-[9px] font-mono px-1 py-0.5 rounded transition-colors
              ${filterTipo === key ? 'bg-[#3a3a6a] text-white' : 'text-gray-600 hover:text-gray-400'}`}
            title={t.label}
          >{t.icon}</button>
        ))}
      </div>

      {/* Formulario de nuevo post-it */}
      {showForm && (
        <AddPostItForm onAdd={handleAdd} onClose={() => setShowForm(false)} />
      )}

      {/* Post-its */}
      <div
        className="flex-1 overflow-y-auto overflow-x-hidden"
        style={{
          display: 'flex', flexDirection: 'column', gap: 14,
          paddingBottom: 8, paddingRight: 4,
          scrollbarWidth: 'thin',
        }}
      >
        {filtered.length === 0 && (
          <p className="text-[10px] font-mono text-gray-600 italic mt-2 text-center">
            {filterTipo === 'todos' ? 'Sin post-its aún.' : 'Sin notas de este tipo.'}
          </p>
        )}
        {filtered.map((item, i) => (
          <PostIt
            key={item.id}
            item={item}
            index={i}
            onDelete={handleDelete}
            onToggle={handleToggle}
          />
        ))}
      </div>
    </div>
  )
}
