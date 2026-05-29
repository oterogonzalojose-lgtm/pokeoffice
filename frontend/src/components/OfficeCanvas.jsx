import { useEffect, useRef, useState } from 'react'

// ── Canvas ────────────────────────────────────────────────────────────────────
const VW = 800, VH = 760

// ── Sprite paths ──────────────────────────────────────────────────────────────
const SPRITE_PATHS = {
  room:              '/sprites/room_bg.png',
  vp:                '/sprites/vp.png',
  atencion_cliente:  '/sprites/agent_green.png',
  programador:       '/sprites/agent_dark.png',
  marketing:         '/sprites/agent_cyan.png',
  contador:          '/sprites/agent_orange.png',
  proveedores:       '/sprites/agent_purple.png',
}

// ── Character screen positions (pixels in canvas) ─────────────────────────────
// Calibrate these to match where agents sit in room_bg.png
const AGENT_POS = {
  atencion_cliente: { x: 125, y: 562 },
  programador:      { x: 218, y: 562 },
  marketing:        { x: 312, y: 562 },
  contador:         { x: 534, y: 562 },
  proveedores:      { x: 639, y: 562 },
}
const VP_HOME = { x: 400, y: 660 }

// Agent sprite dimensions (px in canvas)
const AGENT_W = 52, AGENT_H = 68
const VP_W    = 52, VP_H    = 80

// ── Agent colors (fallback when sprite is missing) ────────────────────────────
const AGENT_COLORS = {
  atencion_cliente: '#27AE60',
  programador:      '#607D8B',
  marketing:        '#E91E63',
  contador:         '#F39C12',
  proveedores:      '#8E44AD',
  vp:               '#4A90D9',
}

// ── State glow colors ─────────────────────────────────────────────────────────
const STATE_GLOW = {
  thinking:      'rgba(255,220,30,0.95)',
  communicating: 'rgba(52,152,219,0.95)',
  working:       'rgba(46,204,113,0.95)',
  done:          'rgba(39,174,96,0.75)',
}

// ── Sprite loader ─────────────────────────────────────────────────────────────
function loadImage(src) {
  return new Promise(resolve => {
    const img = new Image()
    img.onload  = () => resolve(img)
    img.onerror = () => resolve(null)   // missing sprite → null (use placeholder)
    img.src = src
  })
}

// ── Placeholder: colored silhouette when sprite not loaded ────────────────────
function drawPlaceholderAgent(ctx, x, y, color) {
  ctx.fillStyle = color + 'cc'
  ctx.fillRect(x - 14, y - 52, 28, 52)
  ctx.fillStyle = color
  ctx.beginPath(); ctx.arc(x, y - 58, 10, 0, Math.PI * 2); ctx.fill()
}

function drawPlaceholderVP(ctx, x, y, bob) {
  ctx.fillStyle = '#4A90D9cc'
  ctx.fillRect(x - 16, y - 64 + bob, 32, 64)
  ctx.fillStyle = '#4A90D9'
  ctx.beginPath(); ctx.arc(x, y - 70 + bob, 12, 0, Math.PI * 2); ctx.fill()
}

// ── Glow ring ─────────────────────────────────────────────────────────────────
function drawGlow(ctx, x, y, color, rx = 24, ry = 10, lw = 4) {
  ctx.save()
  ctx.strokeStyle = color
  ctx.lineWidth = lw
  ctx.shadowColor = color
  ctx.shadowBlur = 10
  ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); ctx.stroke()
  ctx.restore()
}

// ── Thinking dots ─────────────────────────────────────────────────────────────
function drawThinkingDots(ctx, x, y, frame) {
  for (let i = 0; i < 3; i++) {
    const a = (Math.sin(frame * 0.14 + i * 1.1) + 1) / 2
    ctx.fillStyle = `rgba(255,220,30,${a})`
    ctx.fillRect(Math.round(x + 18 + i * 8), y, 6, 6)
  }
}

// ── Speech bubble ─────────────────────────────────────────────────────────────
function drawBubble(ctx, x, y, text) {
  const t  = text.slice(0, 26)
  const tw = t.length * 5 + 20, th = 18, r = 4
  const bx = x - tw / 2, by = y - 14

  ctx.fillStyle = '#fffde8'
  ctx.strokeStyle = '#c8a020'
  ctx.lineWidth = 1.5

  ctx.beginPath()
  ctx.moveTo(bx + r, by)
  ctx.lineTo(bx + tw - r, by); ctx.arcTo(bx + tw, by, bx + tw, by + r, r)
  ctx.lineTo(bx + tw, by + th - r); ctx.arcTo(bx + tw, by + th, bx + tw - r, by + th, r)
  ctx.lineTo(x + 5, by + th); ctx.lineTo(x, by + th + 7); ctx.lineTo(x - 5, by + th)
  ctx.lineTo(bx + r, by + th); ctx.arcTo(bx, by + th, bx, by + th - r, r)
  ctx.lineTo(bx, by + r); ctx.arcTo(bx, by, bx + r, by, r)
  ctx.closePath()
  ctx.fill(); ctx.stroke()

  ctx.fillStyle = '#301800'
  ctx.font = '7px monospace'
  ctx.textAlign = 'center'
  ctx.fillText(t, x, by + 12)
}

// ── Main component ────────────────────────────────────────────────────────────
export default function OfficeCanvas({ agents, agentStates, lastUserMessage }) {
  const canvasRef      = useRef(null)
  const rafRef         = useRef(null)
  const frameRef       = useRef(0)
  const agentStatesRef = useRef(agentStates)
  const lastMsgRef     = useRef(lastUserMessage ?? '')
  const agentMapRef    = useRef({})
  const vpPosRef       = useRef({ ...VP_HOME })
  const spritesRef     = useRef({})
  const [ready, setReady] = useState(false)

  agentStatesRef.current = agentStates
  lastMsgRef.current     = lastUserMessage ?? ''
  agentMapRef.current    = Object.fromEntries((agents ?? []).map(a => [a.id, a]))

  // Load all sprites once
  useEffect(() => {
    Promise.all(
      Object.entries(SPRITE_PATHS).map(async ([key, src]) => {
        spritesRef.current[key] = await loadImage(src)
      })
    ).then(() => setReady(true))
  }, [])

  // Render loop
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    ctx.imageSmoothingEnabled = false

    function render() {
      frameRef.current++
      const frame    = frameRef.current
      const sp       = spritesRef.current
      const agentMap = agentMapRef.current
      const states   = agentStatesRef.current || {}

      ctx.clearRect(0, 0, VW, VH)

      // ── 1. Room background ────────────────────────────────────────────────
      if (sp.room) {
        ctx.drawImage(sp.room, 0, 0, VW, VH)
      } else {
        // Placeholder while room_bg.png is missing
        ctx.fillStyle = '#2a1e10'
        ctx.fillRect(0, 0, VW, VH)
        ctx.fillStyle = 'rgba(255,255,255,0.12)'
        ctx.font = '14px monospace'
        ctx.textAlign = 'center'
        ctx.fillText('Colocá room_bg.png en /public/sprites/', VW / 2, VH / 2 - 12)
        ctx.fillText('Ver README_SPRITES.md para instrucciones', VW / 2, VH / 2 + 12)
      }

      // ── 2. VP movement target ─────────────────────────────────────────────
      const activeId = Object.entries(states).find(
        ([id, s]) => id !== 'vp' && s.state !== 'idle' && s.state !== 'done'
      )?.[0]

      let tx = VP_HOME.x, ty = VP_HOME.y
      if (activeId && AGENT_POS[activeId]) {
        tx = AGENT_POS[activeId].x
        ty = AGENT_POS[activeId].y + 80
      }
      vpPosRef.current.x += (tx - vpPosRef.current.x) * 0.05
      vpPosRef.current.y += (ty - vpPosRef.current.y) * 0.05

      // ── 3. Collect drawables (painter's algorithm by Y) ───────────────────
      const drawables = []

      // Agents
      Object.entries(AGENT_POS).forEach(([id, pos]) => {
        const agent  = agentMap[id]
        const color  = agent?.color ?? AGENT_COLORS[id] ?? '#888'
        const st     = states[id] ?? {}
        const sstate = st.state ?? 'idle'

        drawables.push({
          y: pos.y,
          draw: () => {
            // Glow ring
            const glow = STATE_GLOW[sstate]
            if (glow) drawGlow(ctx, pos.x, pos.y + 12, glow)

            // Sprite or placeholder
            const img = sp[id]
            if (img) {
              ctx.drawImage(img, pos.x - AGENT_W / 2, pos.y - AGENT_H, AGENT_W, AGENT_H)
            } else {
              drawPlaceholderAgent(ctx, pos.x, pos.y, color)
            }

            // Thinking dots
            if (sstate === 'thinking') {
              drawThinkingDots(ctx, pos.x, pos.y - AGENT_H - 4, frame)
            }

            // Message bubble
            if (st.message && sstate !== 'idle' && sstate !== 'done') {
              drawBubble(ctx, pos.x, pos.y - AGENT_H - 8, st.message)
            }
          },
        })
      })

      // VP
      const vpX  = Math.round(vpPosRef.current.x)
      const vpY  = Math.round(vpPosRef.current.y)
      const bob  = Math.round(Math.sin(frame * 0.07) * 1.5)
      const vpSt = states['vp'] ?? {}
      const glow = STATE_GLOW[vpSt.state ?? '']

      drawables.push({
        y: vpY,
        draw: () => {
          if (glow) drawGlow(ctx, vpX, vpY + 14, glow, 26, 11, 5)

          const img = sp.vp
          if (img) {
            ctx.drawImage(img, vpX - VP_W / 2, vpY - VP_H + 16 + bob, VP_W, VP_H)
          } else {
            drawPlaceholderVP(ctx, vpX, vpY, bob)
          }

          // VP label badge
          ctx.fillStyle = 'rgba(6,8,20,0.80)'
          ctx.fillRect(vpX - 13, vpY + 6, 26, 12)
          ctx.fillStyle = '#ffffff'
          ctx.font = 'bold 8px monospace'
          ctx.textAlign = 'center'
          ctx.fillText('VP', vpX, vpY + 15)

          // Speech bubble
          if (vpSt.message && vpSt.state !== 'idle' && vpSt.state !== 'done') {
            drawBubble(ctx, vpX, vpY - VP_H, vpSt.message)
          }

          // Thinking dots
          if (vpSt.state === 'thinking') {
            drawThinkingDots(ctx, vpX, vpY - VP_H - 6, frame)
          }
        },
      })

      // Sort back-to-front by Y
      drawables.sort((a, b) => a.y - b.y)
      drawables.forEach(d => d.draw())

      rafRef.current = requestAnimationFrame(render)
    }

    render()
    return () => cancelAnimationFrame(rafRef.current)
  }, [ready])

  return (
    <canvas
      ref={canvasRef}
      width={VW}
      height={VH}
      style={{ display: 'block', maxWidth: '100%', imageRendering: 'pixelated' }}
      className="pixel-border"
    />
  )
}
