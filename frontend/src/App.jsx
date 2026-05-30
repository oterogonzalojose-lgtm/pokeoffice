import { useState, useEffect, useCallback } from 'react'
import AdminLogin from './components/AdminLogin'
import AdminPanel from './components/AdminPanel'
import LoginScreen from './components/LoginScreen'
import OfficeCanvas from './components/OfficeCanvas'
import { apiFetch, getToken, clearToken } from './utils/api'
import ChatInput from './components/ChatInput'
import ActivityFeed from './components/ActivityFeed'
import PostItBoard from './components/PostItBoard'
import Dashboard from './components/Dashboard'
import Onboarding, { SheetsIcon } from './components/Onboarding'
import ConversationHistory from './components/ConversationHistory'
import { useWebSocket } from './hooks/useWebSocket'

// En producción (Railway) el frontend se sirve desde el mismo origen → URL relativa ''
// En desarrollo Vite usa .env.development → VITE_API_URL=http://localhost:8000
const API = import.meta.env.VITE_API_URL ?? ''

const AGENT_INFO = [
  { id: 'vp',               color: '#4A90D9', name: 'VP',       desc: 'Orquesta y delega' },
  { id: 'atencion_cliente', color: '#27AE60', name: 'Recep',    desc: 'Clientes y turnos' },
  { id: 'contador',         color: '#F39C12', name: 'Cont',     desc: 'Finanzas y balances' },
  { id: 'proveedores',      color: '#8E44AD', name: 'Prov',     desc: 'Compras e inventario' },
  { id: 'marketing',        color: '#E91E63', name: 'Mktg',     desc: 'Redes y campañas' },
  { id: 'programador',      color: '#607D8B', name: 'Dev',      desc: 'Código y sistemas' },
]

const CONNECTIONS = [
  { icon: '📊', name: 'Google Sheets',  desc: 'Planilla Maestra',  status: true  },
  { icon: '🤖', name: 'Claude API',     desc: 'Anthropic AI',      status: true  },
  { icon: '📱', name: 'WhatsApp',       desc: 'Próximamente',      status: false },
  { icon: '📧', name: 'Email',          desc: 'Próximamente',      status: false },
]

function SidebarPanel({ feedEvents }) {
  const [tab, setTab] = useState('actividad')
  return (
    <div className="flex flex-col gap-1" style={{ minHeight: 360 }}>
      {/* Tab selector */}
      <div className="flex gap-1">
        {[['actividad','📋 Actividad'], ['dashboard','📊 Dashboard'], ['historial','🕐 Historial']].map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`text-[10px] font-mono px-2 py-1 rounded transition-colors flex-1
              ${tab === key
                ? 'bg-[#1e1e3a] text-white border border-[#3a3a6a]'
                : 'text-gray-500 hover:text-gray-300 border border-transparent'}`}>
            {label}
          </button>
        ))}
      </div>
      {/* Panel content */}
      <div className="bg-[#07070f] border border-[#1e1e3a] rounded flex flex-col"
           style={{ height: 400 }}>
        {tab === 'actividad' && <ActivityFeed events={feedEvents} />}
        {tab === 'dashboard' && <Dashboard />}
        {tab === 'historial' && <ConversationHistory />}
      </div>
    </div>
  )
}

// ── Admin route ───────────────────────────────────────────────────────────────

function AdminRoute() {
  const [token, setAdminToken] = useState(() => localStorage.getItem('admin_token'))
  function handleLogout() { localStorage.removeItem('admin_token'); setAdminToken(null) }
  if (!token) return <AdminLogin onLogin={setAdminToken} />
  return <AdminPanel token={token} onLogout={handleLogout} />
}

// ── App autenticada (todos los hooks van acá, sin early returns) ──────────────

function AuthenticatedApp() {
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [negocioConfig, setNegocioConfig]   = useState(null)
  const [agents, setAgents]                 = useState([])
  const [agentStates, setAgentStates]       = useState({})
  const [feedEvents, setFeedEvents]         = useState([])
  const [loading, setLoading]               = useState(false)
  const [lastUserMessage, setLastUserMessage] = useState('')
  const [newReminder, setNewReminder]       = useState(null)
  const [planillaUrl, setPlanillaUrl]       = useState(null)

  useEffect(() => {
    apiFetch('/config')
      .then(r => r.json())
      .then(cfg => {
        setNegocioConfig(cfg)
        if (!cfg.onboarding_completado) setShowOnboarding(true)
      })
      .catch(() => setShowOnboarding(true))

    apiFetch('/planilla')
      .then(r => r.json())
      .then(p => { if (p.configured && p.url) setPlanillaUrl(p.url) })
      .catch(() => {})

    apiFetch('/agents')
      .then(r => r.json())
      .then(data => {
        setAgents(data)
        const initial = {}
        data.forEach(a => { initial[a.id] = { state: 'idle', message: '' } })
        setAgentStates(initial)
      })
      .catch(() => {})
  }, [])

  const handleWsEvent = useCallback((ev) => {
    setFeedEvents(prev => [...prev.slice(-300), ev])
    if (ev.type === 'agent_state') {
      setAgentStates(prev => ({ ...prev, [ev.agent]: { state: ev.state, message: ev.message } }))
    }
    if (ev.type === 'vp_response') setLoading(false)
    if (ev.type === 'recordatorio_nuevo') setNewReminder(ev.recordatorio)
  }, [])

  useWebSocket(handleWsEvent)

  async function handleSend(message) {
    setLoading(true)
    setLastUserMessage(message)
    setFeedEvents(prev => [...prev, { type: 'user', message }])
    try {
      await apiFetch('/message', {
        method: 'POST',
        body: JSON.stringify({ message }),
      })
    } catch {
      setFeedEvents(prev => [...prev, { type: 'error', message: 'Error de conexión.' }])
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a18] flex flex-col items-center py-4 px-4 gap-3">
      {showOnboarding && (
        <Onboarding onComplete={cfg => {
          setNegocioConfig(cfg)
          setShowOnboarding(false)
          if (cfg.planillaUrl) setPlanillaUrl(cfg.planillaUrl)
        }} />
      )}

      {/* Header */}
      <header className="w-full max-w-[980px] flex items-center gap-3">
        <span className="text-3xl">🏢</span>
        <div>
          <h1 className="text-xl font-bold text-white tracking-widest uppercase font-mono">Pokeoffice</h1>
          <p className="text-xs text-gray-500 font-mono">Tu mini oficina con IA</p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {negocioConfig?.nombre_negocio && (
            <span className="text-xs font-mono text-gray-600 hidden sm:block">
              {negocioConfig.nombre_negocio}
            </span>
          )}
          {planillaUrl && (
            <a href={planillaUrl} target="_blank" rel="noreferrer"
              title="Abrir planilla maestra en Google Sheets"
              className="flex items-center gap-1.5 bg-[#0f9d58] hover:bg-[#0d8f50]
                         transition-colors px-2.5 py-1 rounded text-white">
              <SheetsIcon size={14} />
              <span className="text-[10px] font-mono font-bold hidden sm:inline">Planilla</span>
            </a>
          )}
          <button
            onClick={() => setShowOnboarding(true)}
            title="Configuración del negocio"
            className="text-gray-600 hover:text-gray-300 text-sm transition-colors"
          >⚙️</button>
          <button
            onClick={() => { clearToken(); window.location.reload() }}
            title="Cerrar sesión"
            className="text-gray-600 hover:text-red-400 text-sm transition-colors"
          >🚪</button>
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono text-gray-500">{loading ? 'Procesando...' : 'En línea'}</span>
            <div className={`w-2 h-2 rounded-full ${loading ? 'bg-yellow-400 animate-pulse' : 'bg-green-500'}`} />
          </div>
        </div>
      </header>

      {/* Main layout */}
      <div className="w-full max-w-[1200px] flex gap-3">

        {/* Post-it board (izquierda) */}
        <PostItBoard newReminder={newReminder} />

        {/* Canvas + Chat */}
        <div className="flex flex-col gap-2 flex-1">
          <OfficeCanvas agents={agents} agentStates={agentStates} lastUserMessage={lastUserMessage} />
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>

        {/* Sidebar */}
        <div className="w-72 flex flex-col gap-3">
          <SidebarPanel feedEvents={feedEvents} />

          {/* Connections */}
          <div className="flex flex-col gap-1">
            <h2 className="text-[10px] uppercase font-bold text-gray-500 font-mono tracking-widest">
              Conexiones
            </h2>
            <div className="bg-[#07070f] border border-[#1e1e3a] rounded p-2 flex flex-col gap-1.5">
              {CONNECTIONS.map(c => (
                <div key={c.name} className="flex items-center gap-2">
                  <span className="text-base leading-none">{c.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-mono font-bold text-white leading-none">{c.name}</p>
                    <p className="text-[10px] font-mono text-gray-500">{c.desc}</p>
                  </div>
                  <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${c.status ? 'bg-green-500' : 'bg-gray-600'}`} />
                </div>
              ))}
            </div>
          </div>

          {/* Team */}
          <div className="flex flex-col gap-1">
            <h2 className="text-[10px] uppercase font-bold text-gray-500 font-mono tracking-widest">
              Equipo
            </h2>
            <div className="bg-[#07070f] border border-[#1e1e3a] rounded p-2 flex flex-col gap-1.5">
              {AGENT_INFO.map(a => (
                <div key={a.id} className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ background: a.color }} />
                  <span className="text-xs font-mono font-bold text-white w-10 shrink-0">{a.name}</span>
                  <span className="text-[10px] font-mono text-gray-400 truncate">{a.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── App principal ─────────────────────────────────────────────────────────────

export default function App() {
  if (window.location.pathname === '/admin') return <AdminRoute />

  const [userToken, setUserToken] = useState(() => getToken())

  if (!userToken) return <LoginScreen onLogin={() => setUserToken(getToken())} />
  return <AuthenticatedApp />
}
