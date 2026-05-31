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
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <Badge color="#1e3a5f">{m.tipo}</Badge>
                  {m.user_email && (
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#0d2a1a] text-green-400">
                      👤 {m.user_email}
                    </span>
                  )}
                  <span className="text-[10px] font-mono text-gray-600">
                    relevancia {m.relevancia}/10 · {m.usos} usos
                  </span>
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

  const [logs, setLogs]           = useState([])
  const [logFilter, setLogFilter] = useState({ tenant_id: '', path: '' })
  const loadLogs = useCallback(async (filter = logFilter) => {
    const params = new URLSearchParams()
    if (filter.tenant_id) params.set('tenant_id', filter.tenant_id)
    if (filter.path)      params.set('path', filter.path)
    params.set('limit', '300')
    const data = await adminFetch(`/api/admin/logs?${params}`)
    if (data) setLogs(Array.isArray(data) ? data : [])
  }, [adminFetch, logFilter])

  const [platformEvents, setPlatformEvents] = useState([])
  const [evFilter, setEvFilter] = useState({ tipo: '', estado: 'pendiente' })
  const [respuestaForm, setRespuestaForm] = useState({})   // { [eid]: string }
  const [fixes, setFixes] = useState([])
  const [fixResult, setFixResult] = useState(null)
  const [runningFix, setRunningFix] = useState('')
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

  async function executeFix(fixId) {
    setRunningFix(fixId)
    setFixResult(null)
    const result = await adminFetch(`/api/admin/fixes/${fixId}`, { method: 'POST' })
    setFixResult(result)
    setRunningFix('')
  }

  async function responderEvent(eid, nuevo_estado) {
    const respuesta = respuestaForm[eid] || ''
    if (!respuesta.trim()) return
    await adminFetch(`/api/admin/platform-events/${eid}/responder`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ respuesta, nuevo_estado }),
    })
    setRespuestaForm(prev => ({ ...prev, [eid]: '' }))
    loadPlatformEvents()
  }

  useEffect(() => {
    loadTenants()
    const interval = setInterval(loadTenants, 30000)
    return () => clearInterval(interval)
  }, [loadTenants])
  useEffect(() => { if (tab === 'feedback')    loadFeedback() },           [tab, loadFeedback])
  useEffect(() => { if (tab === 'solicitudes') loadSolicitudes() },         [tab, loadSolicitudes])
  useEffect(() => {
    if (tab === 'plataforma') {
      loadPlatformEvents(evFilter)
      adminFetch('/api/admin/fixes').then(data => { if (data) setFixes(Array.isArray(data) ? data : []) })
    }
  }, [tab])  // eslint-disable-line
  useEffect(() => { if (tab === 'logs')        loadLogs(logFilter) },      [tab])  // eslint-disable-line

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
        {[['tenants','🏠 Tenants'], ['solicitudes','📬 Solicitudes'], ['logs','📋 Logs'], ['feedback','💬 Feedback'], ['plataforma','⚙️ Plataforma'], ['docs','📖 Docs']].map(([k, l]) => (
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

            {/* Fixes ejecutables para todos los tenants */}
            {fixes.length > 0 && (
              <div className="bg-[#07070f] border border-[#2a2a4a] rounded p-4 flex flex-col gap-3">
                <h3 className="font-mono text-xs font-bold text-purple-400 uppercase tracking-widest">
                  Ejecutar fix para todos los tenants
                </h3>
                <div className="flex flex-wrap gap-2">
                  {fixes.map(f => (
                    <button key={f.id}
                      onClick={() => executeFix(f.id)}
                      disabled={!!runningFix}
                      title={f.descripcion}
                      className="font-mono text-xs px-3 py-1.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-gray-300 hover:text-white hover:border-purple-800 disabled:opacity-40 transition-colors">
                      {runningFix === f.id ? '⏳ Corriendo...' : f.nombre}
                    </button>
                  ))}
                </div>

                {fixResult && (
                  <div className="flex flex-col gap-1 mt-1">
                    <p className="font-mono text-[10px] text-gray-500">
                      {fixResult.nombre} — {fixResult.tenants_procesados} tenants procesados
                    </p>
                    {(fixResult.resultados || []).map((r, i) => (
                      <div key={i} className={`font-mono text-[10px] px-2 py-1 rounded flex gap-2 ${
                        r.status === 'ok' ? 'bg-[#0a1a0a] text-green-400' : 'bg-[#1a0a0a] text-red-400'
                      }`}>
                        <span className="font-bold shrink-0">{r.tenant}:</span>
                        <span>{r.resultado || r.error}</span>
                      </div>
                    ))}
                    {fixResult.error && (
                      <p className="font-mono text-[10px] text-red-400">{fixResult.error}</p>
                    )}
                  </div>
                )}
              </div>
            )}

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
                  <option value="escalacion">Escalación</option>
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
                    ev.tipo === 'fix' ? 'border-red-900'
                    : ev.tipo === 'escalacion' ? 'border-orange-900'
                    : 'border-blue-900'
                  }`}>
                  {/* Header */}
                  <div className="flex items-start gap-2 justify-between">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                        ev.tipo === 'fix' ? 'bg-red-900 text-red-300'
                        : ev.tipo === 'escalacion' ? 'bg-orange-900 text-orange-300'
                        : 'bg-blue-900 text-blue-300'
                      }`}>
                        {ev.tipo === 'escalacion' ? '🚨 escalación' : ev.tipo}
                      </span>
                      <span className="font-mono text-sm text-white font-bold">{ev.titulo}</span>
                    </div>
                    {/* Aplicabilidad */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="font-mono text-[10px] text-gray-500">Aplicabilidad</span>
                      <div className="w-16 bg-[#1e1e3a] rounded-full h-1.5">
                        <div className={`h-1.5 rounded-full ${ev.tipo === 'fix' ? 'bg-red-500' : ev.tipo === 'escalacion' ? 'bg-orange-500' : 'bg-blue-500'}`}
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

                  {/* Respuesta admin existente */}
                  {ev.respuesta_admin && (
                    <div className="bg-[#0a1a0a] border border-green-900 rounded p-2 flex flex-col gap-1">
                      <span className="font-mono text-[10px] text-green-500 uppercase tracking-wider">Respuesta Admin</span>
                      <p className="font-mono text-xs text-green-300">{ev.respuesta_admin}</p>
                    </div>
                  )}

                  {/* Formulario de respuesta (solo si no hay respuesta aún o es escalacion) */}
                  {(ev.tipo === 'escalacion' || !ev.respuesta_admin) && ev.estado !== 'implementado' && ev.estado !== 'descartado' && (
                    <div className="flex flex-col gap-1 mt-1">
                      <textarea
                        value={respuestaForm[ev.id] || ''}
                        onChange={e => setRespuestaForm(prev => ({ ...prev, [ev.id]: e.target.value }))}
                        placeholder="Escribir respuesta / decisión del admin..."
                        rows={2}
                        className="bg-[#0a0a18] border border-[#2a2a4a] rounded px-2 py-1 font-mono text-xs text-gray-300 focus:outline-none resize-none w-full"
                      />
                      <div className="flex gap-1 justify-end">
                        {[
                          ['en_desarrollo', 'En dev', 'text-yellow-400 border-yellow-900'],
                          ['implementado',  'Implementado', 'text-green-400 border-green-900'],
                          ['descartado',    'Descartar', 'text-red-400 border-red-900'],
                        ].map(([st, label, cls]) => (
                          <button key={st}
                            onClick={() => responderEvent(ev.id, st)}
                            disabled={!(respuestaForm[ev.id] || '').trim()}
                            className={`font-mono text-[10px] px-2 py-1 rounded border ${cls} disabled:opacity-30 transition-opacity`}>
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>
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

        {/* Logs tab */}
        {tab === 'logs' && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="font-mono text-sm font-bold text-white uppercase tracking-widest">Request Logs</h2>
              <div className="flex items-center gap-2 flex-wrap">
                <select value={logFilter.tenant_id}
                  onChange={e => { const f = { ...logFilter, tenant_id: e.target.value }; setLogFilter(f); loadLogs(f) }}
                  className="bg-[#0a0a18] border border-[#1e1e3a] rounded px-2 py-1 font-mono text-xs text-gray-300 focus:outline-none">
                  <option value="">Todos los tenants</option>
                  {tenants.map(t => (
                    <option key={t.id} value={t.id}>{t.nombre_negocio || t.email}</option>
                  ))}
                </select>
                <input value={logFilter.path}
                  onChange={e => setLogFilter(f => ({ ...f, path: e.target.value }))}
                  onKeyDown={e => e.key === 'Enter' && loadLogs(logFilter)}
                  placeholder="filtrar por path..."
                  className="bg-[#0a0a18] border border-[#1e1e3a] rounded px-2 py-1 font-mono text-xs text-gray-300 focus:outline-none w-40" />
                <button onClick={() => loadLogs(logFilter)}
                  className="text-[10px] font-mono text-blue-400 hover:text-blue-300">↻</button>
              </div>
            </div>

            <div className="bg-[#07070f] border border-[#1e1e3a] rounded overflow-x-auto">
              <table className="w-full min-w-[700px]">
                <thead>
                  <tr className="border-b border-[#1e1e3a]">
                    {['Timestamp', 'Tenant', 'Usuario', 'Método', 'Path', 'Status', 'ms'].map(h => (
                      <th key={h} className="px-3 py-2 text-left font-mono text-[10px] text-gray-500 uppercase tracking-widest whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {logs.length === 0
                    ? <tr><td colSpan={7} className="px-3 py-6 text-center font-mono text-xs text-gray-600">Sin registros aún. Los logs aparecen con el próximo request.</td></tr>
                    : logs.map(l => {
                      const status = l.status_code || 0
                      const statusColor = status >= 500 ? 'text-red-400' : status >= 400 ? 'text-yellow-400' : status >= 200 ? 'text-green-400' : 'text-gray-500'
                      const methodColor = { GET: 'text-blue-400', POST: 'text-green-400', PATCH: 'text-yellow-400', DELETE: 'text-red-400' }[l.method] || 'text-gray-400'
                      return (
                        <tr key={l.id} className="border-b border-[#0f0f1f] hover:bg-[#0d0d20] transition-colors">
                          <td className="px-3 py-1.5 font-mono text-[10px] text-gray-500 whitespace-nowrap">{l.created_at?.slice(5, 19)}</td>
                          <td className="px-3 py-1.5 font-mono text-[10px] text-gray-400 whitespace-nowrap">{l.nombre_negocio || l.tenant_id?.slice(0,8) || '—'}</td>
                          <td className="px-3 py-1.5 font-mono text-[10px] text-gray-500 whitespace-nowrap truncate max-w-[120px]">{l.user_email || '—'}</td>
                          <td className={`px-3 py-1.5 font-mono text-[10px] font-bold whitespace-nowrap ${methodColor}`}>{l.method}</td>
                          <td className="px-3 py-1.5 font-mono text-[10px] text-gray-300 max-w-[200px] truncate">{l.path}</td>
                          <td className={`px-3 py-1.5 font-mono text-[10px] font-bold whitespace-nowrap ${statusColor}`}>{status}</td>
                          <td className="px-3 py-1.5 font-mono text-[10px] text-gray-500 whitespace-nowrap">{l.duration_ms}</td>
                        </tr>
                      )
                    })
                  }
                </tbody>
              </table>
            </div>
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
        {/* Docs tab */}
        {tab === 'docs' && (
          <div className="flex flex-col gap-6 max-w-3xl">
            <h2 className="font-mono text-sm font-bold text-white uppercase tracking-widest">Documentación interna</h2>

            {[
              {
                title: '🤖 Agentes',
                rows: [
                  ['VP / Jefe de Gabinete', 'Orquestador. Recibe instrucciones, delega agentes, nunca expone errores técnicos. Tools propias: briefing_cliente, agregar_columna_personalizada.'],
                  ['Recepcionista', 'Alta, búsqueda y actualización de clientes (tab Clientes). Dedup por nombre y teléfono. Soporta columnas personalizadas.'],
                  ['Contador', 'Ingresos, egresos, balances (tab Finanzas). Valida monto > 0 antes de registrar. Dedup por día+monto+categoría.'],
                  ['Gestor de Proveedores', 'Stock: entrada (suma), venta (resta), corrección (reemplaza), precio. Busca antes de registrar. Devuelve precio al VP para que Contador registre el ingreso.'],
                  ['Marketing', 'Posts, copys, newsletters. Solo genera texto — no escribe en Sheets.'],
                  ['Programador', 'Diagnóstico técnico interno. Usa sh._sheets() (respeta env vars Railway). Puede escalar problemas via escalar_problema → platform_event tipo escalación.'],
                  ['Master DEV', 'Background. Se activa si VP menciona "dificultad técnica". Analiza y guarda fix/mejora/escalacion en platform_events. Haiku.'],
                ],
              },
              {
                title: '📋 Tablas SQLite',
                rows: [
                  ['tenants', 'id, email, nombre_negocio, plan, activo, spreadsheet_id (puede ser NULL — usar .get() or "")'],
                  ['users', 'id, tenant_id, email, nombre, activo, last_login — máx 2 activos por tenant'],
                  ['invitaciones', 'id, tenant_id, email, codigo (6 dígitos), usado, expires_at (24h)'],
                  ['conversations', 'id, tenant_id, user_email, user_message, vp_response, events (JSON array)'],
                  ['vp_memoria', 'id, tenant_id, user_email, tipo, aprendizaje, relevancia, usos'],
                  ['configuracion', '(clave, tenant_id) PK compuesta, valor'],
                  ['recordatorios', 'id, tenant_id, texto, tipo, completado'],
                  ['platform_events', 'id, tenant_id, tipo (fix|mejora|escalacion), titulo, descripcion, razonamiento, aplicabilidad, estado, respuesta_admin'],
                  ['request_logs', 'id, tenant_id, user_email, method, path, status_code, duration_ms — max 5000 filas'],
                ],
              },
              {
                title: '🔌 API Admin endpoints',
                rows: [
                  ['GET /api/admin/tenants', 'Lista todos los tenants (sin spreadsheet_id)'],
                  ['POST /api/admin/tenants', 'Crear tenant { email, nombre_negocio, plan }'],
                  ['GET /api/admin/tenants/:id', 'Detalle completo con spreadsheet_id, usuarios, invitaciones, métricas'],
                  ['POST /api/admin/tenants/:id/invite', 'Generar código invitación (6 dígitos, 24h)'],
                  ['POST /api/admin/tenants/:id/vincular-planilla', 'Linkear Google Sheet existente al tenant'],
                  ['POST /api/admin/tenants/:id/crear-planilla', 'Crear sheet nuevo (requiere Drive quota disponible)'],
                  ['GET /api/admin/tenants/:id/memoria', 'VP Memoria del tenant'],
                  ['GET /api/admin/logs', 'Request logs — ?tenant_id=&path=&limit='],
                  ['GET /api/admin/solicitudes', 'Solicitudes de registro pendientes'],
                  ['GET /api/admin/platform-events', 'Eventos Master DEV — ?tipo=fix|mejora|escalacion&estado='],
                  ['PATCH /api/admin/platform-events/:id/estado', 'Cambiar estado del evento'],
                  ['PATCH /api/admin/platform-events/:id/responder', 'Admin responde una escalación { respuesta, nuevo_estado }'],
                  ['GET /api/admin/fixes', 'Lista fixes ejecutables para todos los tenants'],
                  ['POST /api/admin/fixes/:fix_id', 'Ejecutar fix para todos los tenants simultáneamente'],
                  ['GET /api/admin/diagnostico', 'Diagnóstico completo — requiere JWT Bearer (no query param)'],
                ],
              },
              {
                title: '🔐 Auth & seguridad',
                rows: [
                  ['JWT usuario', '30 días — payload: role=user, user_id, tenant_id, email'],
                  ['JWT admin', 'Sin expiración — payload: role=admin. Se invalida cambiando ADMIN_SECRET'],
                  ['WebSocket', 'Aislado por tenant — token en query param ?token=. Broadcast solo al tenant activo.'],
                  ['Límite usuarios', 'Máximo 2 usuarios activos por tenant (plan starter)'],
                  ['Rutas públicas', '/health, /ws, /auth/solicitar, /auth/verificar, /api/admin/*, /assets/*, /sprites/*'],
                  ['Diagnóstico', 'Requiere JWT Bearer — ya no acepta ?pw= (riesgo en logs de Railway)'],
                ],
              },
              {
                title: '⚙️ Variables Railway',
                rows: [
                  ['ANTHROPIC_API_KEY', 'Clave de Anthropic — sonnet-4-6 (VP/agentes), haiku-4-5 (memoria/master_dev/fallback)'],
                  ['ADMIN_PASSWORD', 'Contraseña del panel /admin'],
                  ['ADMIN_SECRET', 'Secret JWT admin — recomendado ≥32 chars'],
                  ['GOOGLE_SERVICE_ACCOUNT_JSON', 'JSON completo de la service account — pokeoffice-agent@pokeoffice.iam.gserviceaccount.com'],
                  ['DATA_DIR', 'Seteado en Dockerfile como /data — no requiere variable manual'],
                ],
              },
              {
                title: '🧪 Testing',
                rows: [
                  ['pytest tests/ -v', '36 tests de regresión — deben pasar antes de cada push'],
                  ['seed_tenants.py', 'Crea 5 tenants de testing con negocios realistas via API REST'],
                  ['stress_test.py', 'Casos positivos, borde, multi-turno y concurrencia 5 tenants simultáneos'],
                  ['completar_seed.py', 'Completa seed usando tenants ya creados (IDs en el script)'],
                  ['Tenants de testing', 'Valentina Masajes | Tornería Villanueva | Taller Quiroga | Sofía Mates | Bruno Express'],
                ],
              },
            ].map(({ title, rows }) => (
              <div key={title} className="bg-[#07070f] border border-[#1e1e3a] rounded overflow-hidden">
                <div className="px-4 py-2 border-b border-[#1e1e3a]">
                  <p className="font-mono text-xs font-bold text-white">{title}</p>
                </div>
                <table className="w-full">
                  <tbody>
                    {rows.map(([k, v], i) => (
                      <tr key={i} className="border-b border-[#0f0f1f] last:border-0">
                        <td className="px-4 py-2 font-mono text-xs text-blue-300 whitespace-nowrap align-top w-56">{k}</td>
                        <td className="px-4 py-2 font-mono text-xs text-gray-400">{v}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}

      </main>
    </div>
  )
}
