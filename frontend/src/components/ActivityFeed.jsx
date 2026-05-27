import { useEffect, useRef } from 'react'

const STATE_LABELS = {
  thinking:      { icon: '💭', color: 'text-yellow-400' },
  working:       { icon: '⚙️', color: 'text-green-400'  },
  communicating: { icon: '💬', color: 'text-blue-400'   },
  done:          { icon: '✅', color: 'text-emerald-400' },
  idle:          { icon: '🪑', color: 'text-gray-500'   },
}

export default function ActivityFeed({ events }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  return (
    <div className="h-full overflow-y-auto flex flex-col gap-1 pr-1">
      {events.length === 0 && (
        <p className="text-gray-600 text-xs italic mt-2">
          Esperando instrucciones del jefe...
        </p>
      )}
      {events.map((ev, i) => {
        if (ev.type === 'agent_state') {
          const meta = STATE_LABELS[ev.state] ?? STATE_LABELS.idle
          return (
            <div key={i} className="text-xs flex gap-1 items-start">
              <span>{meta.icon}</span>
              <span className={`font-bold ${meta.color}`}>{ev.agent}</span>
              <span className="text-gray-400 truncate">{ev.message}</span>
            </div>
          )
        }
        if (ev.type === 'agent_message') {
          return (
            <div key={i} className="text-xs flex gap-1 items-start text-blue-300">
              <span>📨</span>
              <span className="font-bold">{ev.from}</span>
              <span className="text-gray-500">→</span>
              <span className="font-bold">{ev.to}:</span>
              <span className="text-gray-300 truncate">{ev.message}</span>
            </div>
          )
        }
        if (ev.type === 'vp_response') {
          return (
            <div key={i} className="text-xs bg-[#1a2a1a] border-l-2 border-green-500 pl-2 py-1 text-green-300">
              <span className="font-bold">VP: </span>{ev.message}
            </div>
          )
        }
        if (ev.type === 'user') {
          return (
            <div key={i} className="text-xs bg-[#1a1a3a] border-l-2 border-blue-500 pl-2 py-1 text-white">
              <span className="font-bold text-blue-400">Jefe: </span>{ev.message}
            </div>
          )
        }
        return null
      })}
      <div ref={bottomRef} />
    </div>
  )
}
