import { useState, useEffect, useCallback } from 'react'
import OfficeCanvas from './components/OfficeCanvas'
import ChatInput from './components/ChatInput'
import ActivityFeed from './components/ActivityFeed'
import { useWebSocket } from './hooks/useWebSocket'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function App() {
  const [agents, setAgents] = useState([])
  const [agentStates, setAgentStates] = useState({})
  const [agentMessages, setAgentMessages] = useState([])
  const [feedEvents, setFeedEvents] = useState([])
  const [loading, setLoading] = useState(false)

  // Load agent definitions once
  useEffect(() => {
    fetch(`${API}/agents`)
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
    setFeedEvents(prev => [...prev.slice(-200), ev])

    if (ev.type === 'agent_state') {
      setAgentStates(prev => ({
        ...prev,
        [ev.agent]: { state: ev.state, message: ev.message },
      }))
    }
    if (ev.type === 'agent_message') {
      setAgentMessages(prev => [...prev.slice(-50), ev])
    }
    if (ev.type === 'vp_response') {
      setLoading(false)
    }
  }, [])

  useWebSocket(handleWsEvent)

  async function handleSend(message) {
    setLoading(true)
    setFeedEvents(prev => [...prev, { type: 'user', message }])

    try {
      await fetch(`${API}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      })
    } catch {
      setFeedEvents(prev => [...prev, { type: 'error', message: 'Error de conexión con la oficina.' }])
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#1a1a2e] flex flex-col items-center p-4 gap-4">
      {/* Header */}
      <header className="w-full max-w-[900px] flex items-center gap-3">
        <span className="text-3xl">🏢</span>
        <div>
          <h1 className="text-xl font-bold text-white tracking-widest uppercase font-mono">
            Pokeoffice
          </h1>
          <p className="text-xs text-gray-500 font-mono">Tu mini oficina con IA</p>
        </div>
        <div className={`ml-auto w-2 h-2 rounded-full ${loading ? 'bg-yellow-400 animate-pulse' : 'bg-green-500'}`} />
      </header>

      {/* Main layout */}
      <div className="w-full max-w-[900px] flex gap-4">
        {/* Office canvas */}
        <div className="flex-1 flex flex-col gap-3">
          <OfficeCanvas
            agents={agents}
            agentStates={agentStates}
            agentMessages={agentMessages}
          />
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>

        {/* Activity feed */}
        <div className="w-64 flex flex-col">
          <h2 className="text-xs uppercase font-bold text-gray-500 font-mono mb-2 tracking-widest">
            Actividad
          </h2>
          <div className="flex-1 bg-[#0d0d1f] pixel-border p-2" style={{ minHeight: 380, maxHeight: 420 }}>
            <ActivityFeed events={feedEvents} />
          </div>
        </div>
      </div>

      {/* Agent legend */}
      <div className="w-full max-w-[900px] flex flex-wrap gap-2">
        {agents.map(a => (
          <div key={a.id} className="flex items-center gap-1 text-xs font-mono text-gray-400">
            <span className="w-3 h-3 rounded-none" style={{ background: a.color }} />
            {a.name}
          </div>
        ))}
      </div>
    </div>
  )
}
