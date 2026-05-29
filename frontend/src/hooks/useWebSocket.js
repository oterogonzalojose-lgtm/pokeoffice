import { useEffect, useRef, useCallback } from 'react'
import { getWsUrl } from '../utils/api'

export function useWebSocket(onEvent) {
  const ws = useRef(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    let reconnectTimer = null
    let unmounted = false

    function connect() {
      if (unmounted) return
      ws.current = new WebSocket(getWsUrl())

      ws.current.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          onEventRef.current(data)
        } catch {}
      }

      ws.current.onclose = () => {
        if (!unmounted) reconnectTimer = setTimeout(connect, 3000)
      }

      const pingInterval = setInterval(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send('ping')
        }
      }, 25000)

      ws.current._pingInterval = pingInterval
    }

    connect()

    return () => {
      unmounted = true
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
