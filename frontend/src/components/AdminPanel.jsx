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
      fetch(`${API}/admin/tenants/${tid}`, { headers }).then(r => r.json()),
      fetch(`${API}/admin/tenants/${tid}/memoria`, { headers }).then(r => r.json()),
    ])
    setData(det)
    setMemoria(mem)
    setLoading(false)
  }, [tid])

  useEffect(() => { load() }, [load])

  async function handleInvite(e) {
    e.preventDefault()
    setInviteMsg('')
    const res = await fetch(`${API}/admin/tenants/${tid}/invite`, {
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

function TenantRow({ t, onSelect }) {
  return (
    <tr className="border-b border-[#1e1e3a] hover:bg-[#0d0d20] cursor-pointer transition-colors" onClick={() => onSelect(t.id)}>
      <td className="px-3 py-2.5">
        <p className="font-mono text-sm text-white">{t.nombre_negocio || '(sin nombre)'}</p>
        <p className="font-mono text-xs text-gray-500">{t.email}</p>
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

  const loadTenants = useCallback(async () => {
    setLoading(true)
    const data = await fetch(`${API}/admin/tenants`, { headers }).then(r => r.json())
    setTenants(Array.isArray(data) ? data : [])
    setLoading(false)
  }, [])

  const loadFeedback = useCallback(async () => {
    const data = await fetch(`${API}/admin/feedback`, { headers }).then(r => r.json())
    setFeedback(Array.isArray(data) ? data : [])
  }, [])

  useEffect(() => { loadTenants() }, [loadTenants])
  useEffect(() => { if (tab === 'feedback') loadFeedback() }, [tab, loadFeedback])

  async function handleCreateTenant(e) {
    e.preventDefault()
    setFormMsg('')
    const res = await fetch(`${API}/admin/tenants`, {
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
    await fetch(`${API}/admin/feedback/${fid}/leer`, { method: 'PATCH', headers })
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
        {[['tenants','🏠 Tenants'], ['feedback','💬 Feedback']].map(([k, l]) => (
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
