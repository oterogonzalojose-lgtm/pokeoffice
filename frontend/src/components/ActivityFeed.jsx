import { useEffect, useRef } from 'react'

const AGENT_COLORS = {
  vp:               '#4A90D9',
  atencion_cliente: '#27AE60',
  contador:         '#F39C12',
  proveedores:      '#8E44AD',
  marketing:        '#E91E63',
  programador:      '#607D8B',
}

const AGENT_LABELS = {
  vp:               'VP',
  atencion_cliente: 'Recep',
  contador:         'Cont',
  proveedores:      'Prov',
  marketing:        'Mktg',
  programador:      'Dev',
}

const STATE_CONFIG = {
  thinking:      { icon: '💭', label: 'Pensando',     color: '#F39C12' },
  working:       { icon: '⚙️', label: 'Trabajando',   color: '#27AE60' },
  communicating: { icon: '💬', label: 'Comunicando',  color: '#4A90D9' },
  done:          { icon: '✅', label: 'Listo',        color: '#2ECC71' },
  idle:          { icon: '🪑', label: 'En espera',    color: '#4a4a6a' },
}

export default function ActivityFeed({ events }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  if (events.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-gray-600 text-xs font-mono italic text-center px-4">
          Esperando instrucciones del jefe...
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto flex flex-col gap-1.5 p-2">
      {events.map((ev, i) => {

        // ── Mensaje del jefe ─────────────────────────────────────────────
        if (ev.type === 'user') {
          return (
            <div key={i} className="rounded border border-[#2a3a6a] bg-[#0e0e2a] p-2">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-[10px] font-bold font-mono text-blue-400 uppercase tracking-wide">
                  👤 Jefe
                </span>
              </div>
              <p className="text-xs font-mono text-white leading-relaxed">{ev.message}</p>
            </div>
          )
        }

        // ── Respuesta del VP ─────────────────────────────────────────────
        if (ev.type === 'vp_response') {
          return (
            <div key={i} className="rounded border border-[#1a4a2a] bg-[#0a1a0e] p-2">
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-2 h-2 rounded-full bg-[#4A90D9]" />
                <span className="text-[10px] font-bold font-mono text-[#4A90D9] uppercase tracking-wide">
                  VP · Respuesta
                </span>
              </div>
              <p className="text-xs font-mono text-green-200 leading-relaxed">{ev.message}</p>
            </div>
          )
        }

        // ── Estado de agente ─────────────────────────────────────────────
        if (ev.type === 'agent_state') {
          const sc    = STATE_CONFIG[ev.state] ?? STATE_CONFIG.idle
          const color = AGENT_COLORS[ev.agent] ?? '#888'
          const label = AGENT_LABELS[ev.agent] ?? ev.agent
          if (ev.state === 'idle') return null   // skip idle spam

          return (
            <div key={i} className="flex items-start gap-2 px-1 py-0.5">
              <span className="text-sm leading-none mt-0.5 shrink-0">{sc.icon}</span>
              <div className="flex flex-col gap-0.5 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span
                    className="text-[10px] font-bold font-mono uppercase tracking-wide"
                    style={{ color }}
                  >
                    {label}
                  </span>
                  <span
                    className="text-[10px] font-mono"
                    style={{ color: sc.color }}
                  >
                    {sc.label}
                  </span>
                </div>
                {ev.message && (
                  <p className="text-[10px] font-mono text-gray-400 leading-relaxed truncate">
                    {ev.message}
                  </p>
                )}
              </div>
            </div>
          )
        }

        // ── Mensaje entre agentes ────────────────────────────────────────
        if (ev.type === 'agent_message') {
          const fromColor = AGENT_COLORS[ev.from] ?? '#888'
          const toColor   = AGENT_COLORS[ev.to]   ?? '#888'
          const fromLabel = AGENT_LABELS[ev.from]  ?? ev.from
          const toLabel   = AGENT_LABELS[ev.to]    ?? ev.to
          return (
            <div key={i} className="flex items-start gap-2 px-1 py-0.5">
              <span className="text-sm leading-none mt-0.5 shrink-0">📨</span>
              <div className="flex flex-col gap-0.5 min-w-0">
                <div className="flex items-center gap-1">
                  <span className="text-[10px] font-bold font-mono" style={{ color: fromColor }}>
                    {fromLabel}
                  </span>
                  <span className="text-[10px] text-gray-600 font-mono">→</span>
                  <span className="text-[10px] font-bold font-mono" style={{ color: toColor }}>
                    {toLabel}
                  </span>
                </div>
                {ev.message && (
                  <p className="text-[10px] font-mono text-gray-400 leading-relaxed truncate">
                    {ev.message}
                  </p>
                )}
              </div>
            </div>
          )
        }

        // ── Error ────────────────────────────────────────────────────────
        if (ev.type === 'error') {
          return (
            <div key={i} className="rounded border border-red-900 bg-[#1a0808] p-2">
              <span className="text-xs font-mono text-red-400">⚠️ {ev.message}</span>
            </div>
          )
        }

        return null
      })}
      <div ref={bottomRef} />
    </div>
  )
}
