import { useState, useEffect, useCallback } from 'react'

const API = import.meta.env.VITE_API_URL ?? ''

const AGENT_LABELS = {
  atencion_cliente: 'Recepcionista',
  contador: 'Contador',
  proveedores: 'Proveedores',
  marketing: 'Marketing',
  programador: 'Programador',
}

function Badge({ children, color = '#1e1e3a' }) {
  return (
    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded" style={{ background: color, color: '#fff' }}>
      {children}
    </span>
  )
}

function StatBox({ label, value, sub }) {
  return (
    <div className="bg-[#07070f] border border-[#1e1e3a] rounded p-3 flex flex-col gap-0.5">
      <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">{label}</span>
      <span className="text-xl font-mono font-bold text-white">{value ?? '—'}</span>
      {sub && <span className="text-[10px] font-mono text-gray-600">{sub}</span>}
    </div>
  )
}

// ── Planilla panel ────────────────────────────────────────────────────────────

function PlanillaPanel({ tid, token, spreadsheetId: initialSid }) {
  const [sid,      setSid]      = useState(initialSid || '')
  const [input,    setInput]    = useState('')
  const [editing,  setEditing]  = useState(!initialSid)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const headers = { Authorization: `Bearer ${token}` }

  const url = sid ? `https://docs.google.com/spreadsheets/d/${sid}` : null

  async function handleVincular() {
    if (!input.trim()) return
    setLoading(true)
    setError('')
    try {
      let id = input.trim()
      if (id.includes('spreadsheets/d/'))
        id = id.split('spreadsheets/d/')[1].split('/')[0].split('?')[0]
      const res  = await fetch(`${API}/api/admin/tenants/${tid}/vincular-planilla`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ spreadsheet_id: id }),
      })
      const json = await res.json()
      if (json.ok) { setSid(id); setEditing(false); setInput('') }
      else setError(json.detail || 'No se pudo vincular')
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-[#07070f] border border-[#1e1e3a] rounded p-3 flex flex-col gap-2">
      <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Planilla Maestra Google Sheets</p>

      {!editing && url && (
        <div className="flex items-center gap-3">
          <a href={url} target="_blank" rel="noreferrer"
            className="text-xs font-mono text-green-400 hover:text-green-300 underline flex-1 truncate">
            ✓ {sid}
          </a>
          <button onClick={() => setEditing(true)}
            className="text-[10px] font-mono text-gray-500 hover:text-gray-300 shrink-0">
            cambiar
          </button>
        </div>
      )}

      {editing && (
        <div className="flex gap-2 items-center">
          <input
            value={input} onChange={e => setInput(e.target.value)}
            placeholder="URL o ID de la planilla"
            className="flex-1 bg-[#0a0a18] border border-[#2a2a4a] rounded px-2 py-1.5 text-white font-mono text-xs focus:outline-none focus:border-[#4A90D9]"
          />
          <button onClick={handleVincular} disabled={!input.trim() || loading}
            className="bg-[#0f9d58] hover:bg-[#0d8f50] disabled:bg-[#0a3d2a] text-white font-mono text-xs px-3 py-1.5 rounded transition-colors shrink-0">
            {loading ? '...' : 'Vincular'}
          </button>
          {sid && (
            <button onClick={() => { setEditing(false); setInput('') }}
              className="text-[10px] font-mono text-gray-600 hover:text-gray-400">
              cancelar
            </button>
          )}
        </div>
      )}

      {error && <p className="text-[10px] font-mono text-red-400">{error}</p>}
      {!editing && !url && <p className="text-xs font-mono text-gray-600">Sin planilla configurada</p>}
    </div>
  )
}

// ── Detalle de tenant ──────────────────────────────────────────────────────────

function TenantDetail({ tid, token, onBack }) {
  const [data, setData]       = useState(null)
  const [memoria, setMemoria] = useState([])
  const [tab, setTab]         = useState('metricas')
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteMsg, setInviteMsg]     = useState('')
  const [loading, setLoading] = useState(true)

  const headers = { Authorization: `Bearer ${token}` }

  const load = useCallback(async () => {
    setLoading(true)
    const [det, mem] = await Promise.all([
      fetch(`${API}/api/admin/tenants/${tid}`, { headers }).then(r => r.json()),
      fetch(`${API}/api/admin/tenants/${tid}/memoria`, { headers }).then(r => r.json()),
    ])
    setData(det)
    setMemoria(mem)
    setLoading(false)
  }, [tid])

  useEffect(() => { load() }, [load])

  async function handleInvite(e) {
    e.preventDefault()
    setInviteMsg('')
    const res = await fetch(`${API}/api/admin/tenants/${tid}/invite`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: inviteEmail }),
    })
    const json = await res.json()
    if (!res.ok) { setInviteMsg(`Error: ${json.detail}`); return }
    setInviteMsg(`✓ Código generado: ${json.codigo} (válido 24h)`)
    setInviteEmail('')
    load()
  }

  if (loading) return <div className="flex items-center justify-center h-64 text-gray-500 font-mono text-sm">Cargando...</div>
  if (!data)   return null

  const m = data.metricas || {}

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="text-gray-500 hover:text-white font-mono text-sm transition-colors">← Volver</button>
        <div>
          <h2 className="text-white font-mono font-bold text-base">{data.nombre_negocio || '(sin nombre)'}</h2>
          <p className="text-gray-500 font-mono text-xs">{data.email} · Plan: {data.plan} · {data.activo ? '🟢 Activo' : '🔴 Inactivo'}</p>
          <p className="font-mono text-[10px] text-gray-700 select-all">{data.id}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[#1e1e3a] pb-1">
        {[['metricas','📊 Métricas'], ['memoria','🧠 VP Memoria'], ['usuarios','👤 Usuarios'], ['invitar','✉️ Invitar']].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`font-mono text-xs px-3 py-1 rounded-t transition-colors ${tab === k ? 'bg-[#1e1e3a] text-white' : 'text-gray-500 hover:text-gray-300'}`}>
            {l}
          </button>
        ))}
      </div>

      {/* Métricas */}
      {tab === 'metricas' && (
        <div className="flex flex-col gap-4">
          <PlanillaPanel tid={tid} token={token} spreadsheetId={data.spreadsheet_id} />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <StatBox label="Conversaciones" value={m.total_conversaciones} />
            <StatBox label="Últimos 7 días" value={m.conversaciones_7d} />
            <StatBox label="Errores detectados" value={m.errores_detectados} />
            <StatBox label="Última actividad" value={m.ultima_conversacion ? m.ultima_conversacion.slice(0,10) : '—'} />
          </div>
          {m.agentes_top?.length > 0 && (
            <div className="bg-[#07070f] border border-[#1e1e3a] rounded p-3">
              <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-2">Agentes más usados</p>
              <div className="flex flex-col gap-1.5">
                {m.agentes_top.map(({ agente, usos }) => {
                  const maxUsos = m.agentes_top[0].usos || 1
                  return (
                    <div key={agente} className="flex items-center gap-2">
                      <span className="font-mono text-xs text-gray-300 w-28">{AGENT_LABELS[agente] || agente}</span>
                      <div className="flex-1 bg-[#1e1e3a] rounded-full h-1.5">
                        <div className="bg-[#4A90D9] h-1.5 rounded-full" style={{ width: `${(usos / maxUsos) * 100}%` }} />
                      </div>
                      <span className="font-mono text-[10px] text-gray-500 w-6 text-right">{usos}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* VP Memoria */}
      {tab === 'memoria' && (
        <div className="flex flex-col gap-2">
          {memoria.length === 0
            ? <p className="text-gray-600 font-mono text-sm">Sin aprendizajes registrados aún.</p>
            : memoria.map((m, i) => (
              <div key={i} className="bg-[#07070f] border border-[#1e1e3a] rounded p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Badge color="#1e3a5f">{m.tipo}</Badge>
                  <span className="text-[10px] font-mono text-gray-600">relevancia {m.relevancia}/10 · {m.usos} usos</span>
                </div>
                <p className="font-mono text-sm text-gray-200">{m.aprendizaje}</p>
                {m.contexto && <p className="font-mono text-xs text-gray-500 mt-1">{m.contexto}</p>}
              </div>
            ))
          }
        </div>
      )}

      {/* Usuarios */}
      {tab === 'usuarios' && (
        <div className="flex flex-col gap-2">
          <p className="text-[10px] font-mono text-gray-500">{data.users?.length || 0}/2 usuarios</p>
          {(data.users || []).map(u => (
            <div key={u.id} className="bg-[#07070f] border border-[#1e1e3a] rounded p-3 flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full ${u.activo ? 'bg-green-500' : 'bg-gray-600'}`} />
              <div className="flex-1">
                <p className="font-mono text-sm text-white">{u.nombre || u.email}</p>
                <p className="font-mono text-xs text-gray-500">{u.email} · último login: {u.last_login?.slice(0,10) || 'nunca'}</p>
              </div>
            </div>
          ))}
          {(!data.users || data.users.length === 0) && (
            <p className="text-gray-600 font-mono text-sm">Sin usuarios registrados.</p>
          )}
        </div>
      )}

      {/* Invitar */}
      {tab === 'invitar' && (
        <div className="flex flex-col gap-3 max-w-md">
          <p className="font-mono text-xs text-gray-500">
            Genera un código de 6 dígitos válido 24h. Usuarios activos: {data.user_count}/2.
          </p>
          <form onSubmit={handleInvite} className="flex gap-2">
            <input
              type="email"
              value={inviteEmail}
              onChange={e => setInviteEmail(e.target.value)}
              placeholder="email@cliente.com"
              required
              className="flex-1 bg-[#0a0a18] border border-[#1e1e3a] rounded px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-[#4A90D9]"
            />
            <button type="submit"
              className="bg-[#4A90D9] hover:bg-[#3a7bc8] text-white font-mono text-sm px-4 py-2 rounded transition-colors">
              Invitar
            </button>
          </form>
          {inviteMsg && <p className={`font-mono text-xs ${inviteMsg.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>{inviteMsg}</p>}
          {data.invitaciones?.length > 0 && (
            <div className="flex flex-col gap-1 mt-2">
              <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Invitaciones anteriores</p>
              {data.invitaciones.map(inv => (
                <div key={inv.id} className="flex items-center gap-2 text-xs font-mono text-gray-400">
                  <span>{inv.email}</span>
                  <Badge color={inv.usado ? '#1a3a1a' : '#3a1e1e'}>{inv.usado ? 'Usada' : 'Pendiente'}</Badge>
                  <span className="text-gray-600">{inv.created_at?.slice(0,10)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Lista de tenants ───────────────────────────────────────────────────────────

function CopyId({ id }) {
  const [copied, setCopied] = useState(false)
  function copy(e) {
    e.stopPropagation()
    navigator.clipboard?.writeText(id)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <span className="inline-flex items-center gap-1 font-mono text-[10px] text-gray-600">
      {id.slice(0, 8)}…
      <button onClick={copy}
        className="text-gray-700 hover:text-gray-400 transition-colors">
        {copied ? '✓' : 'copiar'}
      </button>
    </span>
  )
}

function TenantRow({ t, onSelect }) {
  return (
    <tr className="border-b border-[#1e1e3a] hover:bg-[#0d0d20] cursor-pointer transition-colors" onClick={() => onSelect(t.id)}>
      <td className="px-3 py-2.5">
        <p className="font-mono text-sm text-white">{t.nombre_negocio || '(sin nombre)'}</p>
        <p className="font-mono text-xs text-gray-500">{t.email}</p>
        <CopyId id={t.id} />
      </td>
      <td className="px-3 py-2.5 font-mono text-xs text-gray-400">{t.plan}</td>
      <td className="px-3 py-2.5 font-mono text-xs text-gray-400 text-center">{t.user_count}/2</td>
      <td className="px-3 py-2.5 font-mono text-xs text-gray-400 text-center">{t.conv_count}</td>
      <td className="px-3 py-2.5 font-mono text-xs text-gray-400 text-center">{t.memoria_count}</td>
      <td className="px-3 py-2.5 text-center">
        <div className={`w-2 h-2 rounded-full mx-auto ${t.activo ? 'bg-green-500' : 'bg-gray-600'}`} />
      </td>
    </tr>
  )
}

// ── Panel principal ────────────────────────────────────────────────────────────

export default function AdminPanel({ token, onLogout }) {
  const [tenants, setTenants]     = useState([])
  const [selected, setSelected]   = useState(null)
  const [tab, setTab]             = useState('tenants')
  const [feedback, setFeedback]   = useState([])
  const [showForm, setShowForm]   = useState(false)
  const [form, setForm]           = useState({ email: '', nombre_negocio: '', plan: 'starter' })
  const [formMsg, setFormMsg]     = useState('')
  const [loading, setLoading]     = useState(true)

  const headers = { Authorization: `Bearer ${token}` }

  const adminFetch = useCallback(async (path, opts = {}) => {
    const res = await fetch(`${API}${path}`, { ...opts, headers: { ...headers, ...opts.headers } })
    if (res.status === 401) { onLogout(); return null }
    return res.json()
  }, [token, onLogout])

  const loadTenants = useCallback(async () => {
    setLoading(true)
    const data = await adminFetch('/api/admin/tenants')
    if (data) setTenants(Array.isArray(data) ? data : [])
    setLoading(false)
  }, [adminFetch])

  const loadFeedback = useCallback(async () => {
    const data = await adminFetch('/api/admin/feedback')
    if (data) setFeedback(Array.isArray(data) ? data : [])
  }, [adminFetch])

  const [solicitudes, setSolicitudes] = useState([])
  const loadSolicitudes = useCallback(async () => {
    const data = await adminFetch('/api/admin/solicitudes')
    if (data) setSolicitudes(Array.isArray(data) ? data : [])
  }, [adminFetch])

  const [platformEvents, setPlatformEvents] = useState([])
  const [evFilter, setEvFilter] = useState({ tipo: '', estado: 'pendiente' })
  const loadPlatformEvents = useCallback(async (filter = evFilter) => {
    const params = new URLSearchParams()
    if (filter.tipo)   params.set('tipo',   filter.tipo)
    if (filter.estado) params.set('estado', filter.estado)
    const data = await adminFetch(`/api/admin/platform-events?${params}`)
    if (data) setPlatformEvents(Array.isArray(data) ? data : [])
  }, [adminFetch, evFilter])

  async function cambiarEstadoEvent(eid, estado) {
    await adminFetch(`/api/admin/platform-events/${eid}/estado?estado=${estado}`, { method: 'PATCH' })
    loadPlatformEvents()
  }

  useEffect(() => {
    loadTenants()
    const interval = setInterval(loadTenants, 30000)
    return () => clearInterval(interval)
  }, [loadTenants])
  useEffect(() => { if (tab === 'feedback')    loadFeedback() },                         [tab, loadFeedback])
  useEffect(() => { if (tab === 'solicitudes') loadSolicitudes() },                       [tab, loadSolicitudes])
  useEffect(() => { if (tab === 'plataforma')  loadPlatformEvents(evFilter) },            [tab])  // eslint-disable-line

  async function handleCreateTenant(e) {
    e.preventDefault()
    setFormMsg('')
    const res = await fetch(`${API}/api/admin/tenants`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
    const json = await res.json()
    if (!res.ok) { setFormMsg(`Error: ${json.detail}`); return }
    setFormMsg('✓ Tenant creado')
    setForm({ email: '', nombre_negocio: '', plan: 'starter' })
    setShowForm(false)
    loadTenants()
  }

  async function markRead(fid) {
    await fetch(`${API}/api/admin/feedback/${fid}/leer`, { method: 'PATCH', headers })
    loadFeedback()
  }

  if (selected) {
    return (
      <div className="min-h-screen bg-[#0a0a18] p-6">
        <TenantDetail tid={selected} token={token} onBack={() => setSelected(null)} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0a0a18] flex flex-col">
      {/* Header */}
      <header className="border-b border-[#1e1e3a] px-6 py-3 flex items-center gap-3">
        <span className="text-2xl">🏢</span>
        <h1 className="font-mono font-bold text-white text-base tracking-widest uppercase">Pokeoffice Admin</h1>
        <div className="ml-auto flex items-center gap-3">
          <span className="font-mono text-xs text-gray-500">{tenants.length} tenants</span>
          <button onClick={onLogout} className="font-mono text-xs text-gray-600 hover:text-gray-300 transition-colors">Salir</button>
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-[#1e1e3a] px-6 flex gap-1 pt-2">
        {[['tenants','🏠 Tenants'], ['solicitudes','📬 Solicitudes'], ['feedback','💬 Feedback'], ['plataforma','⚙️ Plataforma']].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`font-mono text-xs px-3 py-1.5 rounded-t transition-colors ${tab === k ? 'bg-[#1e1e3a] text-white' : 'text-gray-500 hover:text-gray-300'}`}>
            {l}
          </button>
        ))}
      </div>

      <main className="flex-1 p-6">
        {/* Tenants tab */}
        {tab === 'tenants' && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="font-mono text-sm font-bold text-white uppercase tracking-widest">Mini Oficinas</h2>
              <button onClick={() => setShowForm(f => !f)}
                className="bg-[#4A90D9] hover:bg-[#3a7bc8] text-white font-mono text-xs px-3 py-1.5 rounded transition-colors">
                + Nueva cuenta
              </button>
            </div>

            {showForm && (
              <form onSubmit={handleCreateTenant} className="bg-[#07070f] border border-[#1e1e3a] rounded p-4 flex flex-col gap-3 max-w-md">
                <input type="email" required placeholder="Email del cliente"
                  value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  className="bg-[#0a0a18] border border-[#1e1e3a] rounded px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-[#4A90D9]" />
                <input type="text" placeholder="Nombre del negocio"
                  value={form.nombre_negocio} onChange={e => setForm(f => ({ ...f, nombre_negocio: e.target.value }))}
                  className="bg-[#0a0a18] border border-[#1e1e3a] rounded px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-[#4A90D9]" />
                <select value={form.plan} onChange={e => setForm(f => ({ ...f, plan: e.target.value }))}
                  className="bg-[#0a0a18] border border-[#1e1e3a] rounded px-3 py-2 text-white font-mono text-sm focus:outline-none">
                  <option value="starter">Starter</option>
                  <option value="pro">Pro</option>
                </select>
                {formMsg && <p className={`font-mono text-xs ${formMsg.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>{formMsg}</p>}
                <div className="flex gap-2">
                  <button type="submit" className="bg-[#4A90D9] hover:bg-[#3a7bc8] text-white font-mono text-xs px-4 py-2 rounded transition-colors">Crear</button>
                  <button type="button" onClick={() => setShowForm(false)} className="text-gray-500 font-mono text-xs px-4 py-2 rounded hover:text-gray-300">Cancelar</button>
                </div>
              </form>
            )}

            {loading
              ? <p className="font-mono text-sm text-gray-600 animate-pulse">Cargando...</p>
              : tenants.length === 0
                ? <p className="font-mono text-sm text-gray-600">No hay tenants todavía. Creá el primero.</p>
                : (
                  <div className="bg-[#07070f] border border-[#1e1e3a] rounded overflow-hidden">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-[#1e1e3a]">
                          {['Negocio / Email', 'Plan', 'Usuarios', 'Convs', 'Memoria', 'Estado'].map(h => (
                            <th key={h} className="px-3 py-2 text-left font-mono text-[10px] text-gray-500 uppercase tracking-widest">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {tenants.map(t => <TenantRow key={t.id} t={t} onSelect={setSelected} />)}
                      </tbody>
                    </table>
                  </div>
                )
            }
          </div>
        )}

        {/* Solicitudes tab */}
        {tab === 'solicitudes' && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="font-mono text-sm font-bold text-white uppercase tracking-widest">
                Solicitudes de acceso
              </h2>
              <button onClick={loadSolicitudes}
                className="text-[10px] font-mono text-blue-400 hover:text-blue-300 transition-colors">
                ↻ Actualizar
              </button>
            </div>
            {solicitudes.length === 0
              ? <p className="font-mono text-sm text-gray-600">Sin solicitudes pendientes.</p>
              : solicitudes.map(s => (
                <div key={s.id}
                  className="bg-[#07070f] border border-[#2a2a5a] rounded p-3 flex items-start gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-mono text-sm text-white font-bold">{s.nombre || '(sin nombre)'}</span>
                      <span className="font-mono text-xs text-gray-500">{s.email}</span>
                    </div>
                    {s.mensaje && <p className="font-mono text-xs text-gray-400">{s.mensaje}</p>}
                    <p className="font-mono text-[10px] text-gray-600 mt-1">{s.created_at?.slice(0,16)}</p>
                  </div>
                  <button
                    onClick={async () => {
                      await fetch(`${API}/api/admin/solicitudes/${s.id}/atender`, { method: 'PATCH', headers })
                      loadSolicitudes()
                    }}
                    className="text-[10px] font-mono text-green-400 hover:text-green-300 border border-green-900
                               px-2 py-1 rounded transition-colors shrink-0">
                    ✓ Atendida
                  </button>
                </div>
              ))
            }
          </div>
        )}

        {/* Plataforma tab */}
        {tab === 'plataforma' && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="font-mono text-sm font-bold text-white uppercase tracking-widest">
                Master DEV — Eventos de plataforma
              </h2>
              <div className="flex items-center gap-2">
                {/* Filtro tipo */}
                <select value={evFilter.tipo}
                  onChange={e => { const f = { ...evFilter, tipo: e.target.value }; setEvFilter(f); loadPlatformEvents(f) }}
                  className="bg-[#0a0a18] border border-[#1e1e3a] rounded px-2 py-1 font-mono text-xs text-gray-300 focus:outline-none">
                  <option value="">Todos los tipos</option>
                  <option value="fix">Fix</option>
                  <option value="mejora">Mejora</option>
                </select>
                {/* Filtro estado */}
                <select value={evFilter.estado}
                  onChange={e => { const f = { ...evFilter, estado: e.target.value }; setEvFilter(f); loadPlatformEvents(f) }}
                  className="bg-[#0a0a18] border border-[#1e1e3a] rounded px-2 py-1 font-mono text-xs text-gray-300 focus:outline-none">
                  <option value="pendiente">Pendientes</option>
                  <option value="en_desarrollo">En desarrollo</option>
                  <option value="implementado">Implementados</option>
                  <option value="descartado">Descartados</option>
                  <option value="">Todos</option>
                </select>
                <button onClick={() => loadPlatformEvents(evFilter)}
                  className="text-[10px] font-mono text-blue-400 hover:text-blue-300">↻</button>
              </div>
            </div>

            {platformEvents.length === 0
              ? <p className="font-mono text-sm text-gray-600">Sin eventos registrados para estos filtros.</p>
              : platformEvents.map(ev => (
                <div key={ev.id}
                  className={`bg-[#07070f] border rounded p-4 flex flex-col gap-2 ${
                    ev.tipo === 'fix' ? 'border-red-900' : 'border-blue-900'
                  }`}>
                  {/* Header */}
                  <div className="flex items-start gap-2 justify-between">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                        ev.tipo === 'fix'
                          ? 'bg-red-900 text-red-300'
                          : 'bg-blue-900 text-blue-300'
                      }`}>
                        {ev.tipo}
                      </span>
                      <span className="font-mono text-sm text-white font-bold">{ev.titulo}</span>
                    </div>
                    {/* Aplicabilidad */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="font-mono text-[10px] text-gray-500">Aplicabilidad</span>
                      <div className="w-16 bg-[#1e1e3a] rounded-full h-1.5">
                        <div className={`h-1.5 rounded-full ${ev.tipo === 'fix' ? 'bg-red-500' : 'bg-blue-500'}`}
                          style={{ width: `${(ev.aplicabilidad / 10) * 100}%` }} />
                      </div>
                      <span className="font-mono text-[10px] text-gray-400">{ev.aplicabilidad}/10</span>
                    </div>
                  </div>

                  {/* Descripción */}
                  <p className="font-mono text-xs text-gray-300">{ev.descripcion}</p>

                  {/* Razonamiento */}
                  {ev.razonamiento && (
                    <p className="font-mono text-[10px] text-gray-500 italic border-l border-[#2a2a4a] pl-2">
                      {ev.razonamiento}
                    </p>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between flex-wrap gap-2 mt-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-gray-600">
                        {ev.nombre_negocio || ev.tenant_id?.slice(0, 8) || 'Sistema'}
                      </span>
                      <span className="text-gray-700">·</span>
                      <span className="font-mono text-[10px] text-gray-600">{ev.created_at?.slice(0, 16)}</span>
                    </div>
                    {/* Acciones de estado */}
                    <div className="flex items-center gap-1">
                      {[
                        ['pendiente',     'Pendiente',     '#1e1e3a'],
                        ['en_desarrollo', 'En desarrollo', '#1e3a1e'],
                        ['implementado',  'Implementado',  '#0a3d2a'],
                        ['descartado',    'Descartado',    '#3a1e1e'],
                      ].map(([st, label, bg]) => (
                        <button key={st}
                          onClick={() => cambiarEstadoEvent(ev.id, st)}
                          style={{ background: ev.estado === st ? bg : 'transparent' }}
                          className={`font-mono text-[10px] px-2 py-1 rounded border transition-colors ${
                            ev.estado === st
                              ? 'border-gray-600 text-white'
                              : 'border-[#1e1e3a] text-gray-600 hover:text-gray-400'
                          }`}>
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ))
            }
          </div>
        )}

        {/* Feedback tab */}
        {tab === 'feedback' && (
          <div className="flex flex-col gap-3">
            <h2 className="font-mono text-sm font-bold text-white uppercase tracking-widest">Feedback de clientes</h2>
            {feedback.length === 0
              ? <p className="font-mono text-sm text-gray-600">Sin feedback recibido aún.</p>
              : feedback.map(f => (
                <div key={f.id} className={`bg-[#07070f] border rounded p-3 flex gap-3 ${f.leido ? 'border-[#1e1e3a] opacity-60' : 'border-[#2a2a5a]'}`}>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-white font-bold">{f.nombre_negocio || f.email || 'Anónimo'}</span>
                      <span className="font-mono text-[10px] text-gray-500">{f.created_at?.slice(0,16)}</span>
                    </div>
                    <p className="font-mono text-sm text-gray-300">{f.mensaje}</p>
                  </div>
                  {!f.leido && (
                    <button onClick={() => markRead(f.id)}
                      className="text-gray-600 hover:text-gray-300 font-mono text-xs shrink-0 transition-colors">
                      ✓ Leer
                    </button>
                  )}
                </div>
              ))
            }
          </div>
        )}
      </main>
    </div>
  )
}
