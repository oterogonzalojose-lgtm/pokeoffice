import { useEffect, useRef, useCallback } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws'

export function useWebSocket(onEvent) {
  const ws = useRef(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    let reconnectTimer = null

    function connect() {
      ws.current = new WebSocket(WS_URL)

      ws.current.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          onEventRef.current(data)
        } catch {}
      }

      ws.current.onclose = () => {
        reconnectTimer = setTimeout(connect, 3000)
      }

      // keep-alive ping every 25s
      const pingInterval = setInterval(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send('ping')
        }
      }, 25000)

      ws.current._pingInterval = pingInterval
    }

    connect()

    return () => {
      clearTimeout(reconnectTimer)
      clearInterval(ws.current?._pingInterval)
      ws.current?.close()
    }
  }, [])

  const send = useCallback((data) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    }
  }, [])

  return { send }
}
