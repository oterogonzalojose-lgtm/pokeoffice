import { useEffect, useRef } from 'react'
import { Application, Graphics, Text, TextStyle, Container, Ticker } from 'pixi.js'

const FLOOR_COLOR   = 0x2d2d44
const DESK_COLOR    = 0x6b4f2a
const DESK_TOP      = 0x8b6914
const WALL_COLOR    = 0x1a1a2e
const CARPET_COLOR  = 0x2a3a5a

const STATE_COLORS = {
  idle:          0x888888,
  thinking:      0xf1c40f,
  communicating: 0x3498db,
  working:       0x2ecc71,
  done:          0x27ae60,
}

function makeDesk(agent, app) {
  const g = new Container()
  g.x = agent.x
  g.y = agent.y

  // Desk body
  const desk = new Graphics()
  desk.rect(-28, -10, 56, 32).fill(DESK_COLOR)
  desk.rect(-28, -10, 56, 8).fill(DESK_TOP)
  g.addChild(desk)

  // Agent body (pixel character placeholder)
  const body = new Graphics()
  body.roundRect(-10, -32, 20, 24, 2).fill(agent.color)
  body.circle(0, -40, 8).fill(agent.color)
  g.addChild(body)
  g._body = body

  // State indicator dot
  const dot = new Graphics()
  dot.circle(14, -36, 4).fill(STATE_COLORS.idle)
  g.addChild(dot)
  g._dot = dot

  // Name label
  const label = new Text({
    text: agent.name.split('/')[0].trim(),
    style: new TextStyle({ fill: '#e0e0e0', fontSize: 9, fontFamily: 'Courier New' }),
  })
  label.anchor.set(0.5, 0)
  label.y = 24
  g.addChild(label)

  // Speech bubble container (hidden by default)
  const bubble = new Container()
  bubble.visible = false
  const bubbleBg = new Graphics()
  bubbleBg.rect(-50, -50, 100, 36).fill(0xf0f0f0).stroke({ color: 0x333333, width: 2 })
  const bubbleText = new Text({
    text: '',
    style: new TextStyle({ fill: '#111111', fontSize: 8, fontFamily: 'Courier New', wordWrap: true, wordWrapWidth: 92 }),
  })
  bubbleText.x = -46
  bubbleText.y = -46
  bubble.addChild(bubbleBg)
  bubble.addChild(bubbleText)
  g.addChild(bubble)
  g._bubble = bubble
  g._bubbleText = bubbleText
  g._bubbleBg = bubbleBg

  return g
}

export default function OfficeCanvas({ agentStates, agentMessages, agents }) {
  const canvasRef = useRef(null)
  const appRef = useRef(null)
  const nodesRef = useRef({})

  useEffect(() => {
    if (!canvasRef.current || appRef.current) return

    const app = new Application()
    appRef.current = app

    app.init({
      canvas: canvasRef.current,
      width: 720,
      height: 420,
      backgroundColor: WALL_COLOR,
      antialias: false,
    }).then(() => {
      // Floor
      const floor = new Graphics()
      floor.rect(0, 120, 720, 300).fill(FLOOR_COLOR)
      floor.rect(0, 120, 720, 12).fill(CARPET_COLOR)
      app.stage.addChild(floor)

      // Build agent desks
      agents.forEach((agent) => {
        const node = makeDesk(agent, app)
        nodesRef.current[agent.id] = node
        app.stage.addChild(node)
      })
    })

    return () => {
      app.destroy(false)
      appRef.current = null
    }
  }, [agents])

  // React to agent state changes
  useEffect(() => {
    Object.entries(agentStates).forEach(([id, { state, message }]) => {
      const node = nodesRef.current[id]
      if (!node) return

      const color = STATE_COLORS[state] ?? STATE_COLORS.idle
      node._dot.clear().circle(14, -36, 4).fill(color)

      if (state === 'thinking' || state === 'working') {
        node._body.tint = 0xffffff
      } else {
        node._body.tint = 0xffffff
      }

      if (message && state !== 'idle') {
        node._bubble.visible = true
        node._bubbleText.text = message.slice(0, 60)
      } else {
        node._bubble.visible = false
      }
    })
  }, [agentStates])

  // Agent-to-agent message flash
  useEffect(() => {
    if (!agentMessages.length) return
    const last = agentMessages[agentMessages.length - 1]
    const fromNode = nodesRef.current[last.from]
    if (!fromNode) return

    fromNode._bubble.visible = true
    fromNode._bubbleText.text = `→ ${last.to}: ${last.message.slice(0, 50)}`

    const timer = setTimeout(() => {
      if (fromNode._bubble) fromNode._bubble.visible = false
    }, 3000)
    return () => clearTimeout(timer)
  }, [agentMessages])

  return (
    <canvas
      ref={canvasRef}
      className="pixel-border rounded-none"
      style={{ display: 'block', width: '100%', maxWidth: 720 }}
    />
  )
}
