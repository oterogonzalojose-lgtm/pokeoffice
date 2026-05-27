import { useEffect, useRef } from 'react'

// Virtual canvas — rendered at SCALE× for crispy pixels
const SCALE = 2.5
const VW    = 360
const VH    = 240

// ── Palette ──────────────────────────────────────────────────────────────────
const P = {
  floor:      '#DDD0A0', floorDark: '#C8BC8E', floorLine: '#BFB285',
  wall:       '#7A8BAA', wallDark:  '#5A6B8A', wallLight: '#9AABBB',
  desk:       '#9A6020', deskTop:   '#C89040', deskEdge:  '#6A3A08',
  chair:      '#4A5A8A', chairSeat: '#3A4870',
  plant1:     '#36B836', plant2:    '#1E8C1E', plantPot:  '#9A4820',
  window:     '#B0DCF4', winFrame:  '#3A4A6A',
  carpet:     '#5A3575', carpetTrim:'#7A55A5',
  black:      '#111',    skin:      '#FDBCB4',
}

// ── Office layout data ────────────────────────────────────────────────────────
// Each desk: where to draw it, and where the character stands
const LAYOUT = {
  atencion_cliente: { desk: {x:22, y:44, w:44, h:26}, stand: {x:38,  y:84},  label:'Recepcionista' },
  contador:         { desk: {x:82, y:44, w:44, h:26}, stand: {x:98,  y:84},  label:'Contador'      },
  proveedores:      { desk: {x:142,y:44, w:44, h:26}, stand: {x:158, y:84},  label:'Proveedores'   },
  rrhh:             { desk: {x:288,y:62, w:26, h:44}, stand: {x:270, y:82},  label:'RRHH/Legal'    },
  marketing:        { desk: {x:288,y:148,w:26, h:44}, stand: {x:270, y:165}, label:'Marketing'     },
  vp:               { desk: {x:142,y:158,w:56, h:34}, stand: {x:164, y:202}, label:'VP'            },
}

const STATE_COLOR = {
  idle:          '#888',
  thinking:      '#F1C40F',
  communicating: '#3498DB',
  working:       '#2ECC71',
  done:          '#27AE60',
}

// ── Drawing helpers ───────────────────────────────────────────────────────────
function px(ctx, x, y, w, h, color) {
  ctx.fillStyle = color
  ctx.fillRect(x, y, w, h)
}

function drawOfficeBackground(ctx) {
  // Wall (top section)
  px(ctx, 0, 0, VW, 42, P.wallDark)
  px(ctx, 0, 0, VW, 2,  P.wallLight) // top highlight
  px(ctx, 0, 38, VW, 4, P.wall)      // wall/floor junction

  // Windows
  ;[[50,6],[130,6],[210,6]].forEach(([x,y]) => {
    px(ctx, x, y, 32, 24, P.winFrame)
    px(ctx, x+2, y+2, 28, 20, P.window)
    // window panes
    px(ctx, x+2, y+12, 28, 2, P.winFrame)
    px(ctx, x+14, y+2, 2, 20, P.winFrame)
    // reflection
    px(ctx, x+4, y+4, 6, 6, 'rgba(255,255,255,0.25)')
  })

  // Floor
  px(ctx, 0, 42, VW, VH-42, P.floor)

  // Floor grid lines (subtle depth)
  ctx.strokeStyle = P.floorLine
  ctx.lineWidth = 0.4
  for (let gx = 0; gx < VW; gx += 16) {
    ctx.beginPath(); ctx.moveTo(gx, 42); ctx.lineTo(gx, VH); ctx.stroke()
  }
  for (let gy = 42; gy < VH; gy += 16) {
    ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(VW, gy); ctx.stroke()
  }

  // Center carpet
  px(ctx, 90, 108, 140, 50, P.carpet)
  px(ctx, 92, 110, 136, 46, P.carpetTrim)
  px(ctx, 94, 112, 132, 42, P.carpet)

  // Left wall
  px(ctx, 0, 42, 18, VH-42, P.wallDark)
  px(ctx, 16, 42, 2, VH-42, P.wallLight)

  // Right wall
  px(ctx, VW-18, 42, 18, VH-42, P.wallDark)
  px(ctx, VW-18, 42, 2, VH-42, P.wallLight)

  // Plants — corners
  ;[[4,54],[4,144],[VW-22,54],[VW-22,144]].forEach(([x,y]) => {
    px(ctx, x+4, y+14, 10, 8, P.plantPot)     // pot
    px(ctx, x+5, y+12, 8,  4, '#7A3010')       // pot rim
    px(ctx, x,   y+4,  18, 12, P.plant1)       // foliage outer
    px(ctx, x+2, y,    14, 12, P.plant2)        // foliage inner
    px(ctx, x+5, y+2,  8,  8,  '#2AB02A')       // foliage highlight
  })
}

function drawDesk(ctx, d, isVP = false) {
  const {x, y, w, h} = d
  const sideways = w < h   // right-wall desks are taller than wide

  // Desk shadow
  px(ctx, x+3, y+h, w, 3, 'rgba(0,0,0,0.18)')

  // Desk surface
  px(ctx, x, y, w, h, P.deskTop)

  // Desk edge (front face — depth illusion)
  px(ctx, x, y+h-5, w, 5, P.desk)
  px(ctx, x, y, w, 3,  P.deskEdge)  // top edge highlight

  if (!sideways) {
    // Computer/items on desk
    px(ctx, x+w/2-6, y+6,  12, 8, '#333')  // monitor bezel
    px(ctx, x+w/2-5, y+7,  10, 6, '#5A8FC0') // screen
    if (isVP) {
      // VP gets a bigger monitor + nameplate
      px(ctx, x+4, y+h-12, 14, 6, '#C89040') // nameplate
      px(ctx, x+w-16, y+6,  10, 8, '#333')
    } else {
      px(ctx, x+4, y+h-10, 8, 4, '#EEE')     // papers
    }
  } else {
    px(ctx, x+3, y+h/2-6, w-6, 12, '#333')   // sideways monitor
    px(ctx, x+4, y+h/2-5, w-8, 10, '#5A8FC0')
  }

  // Chair behind desk
  const cx = x + w/2 - 6
  const cy = sideways ? y + h + 2 : y - 12
  if (!sideways) {
    px(ctx, cx, cy, 12, 10, P.chair)
    px(ctx, cx+1, cy+1, 10, 7, P.chairSeat)
    px(ctx, cx+3, cy-4, 6, 5, P.chair) // chair back
  }
}

// Pixel-art character sprite (top-down, ~14×18 virtual px)
function drawCharacter(ctx, x, y, color, state, frame, agentId) {
  const bx = Math.round(x - 7)
  const by = Math.round(y - 18)

  // Ground shadow
  ctx.fillStyle = 'rgba(0,0,0,0.22)'
  ctx.beginPath()
  ctx.ellipse(x, y, 7, 4, 0, 0, Math.PI*2)
  ctx.fill()

  // Shoes
  px(ctx, bx+2, by+16, 4, 2, '#222')
  px(ctx, bx+8, by+16, 4, 2, '#222')

  // Legs (animate when communicating)
  const legSwing = state === 'communicating' ? Math.sin(frame*0.25)*2 : 0
  px(ctx, bx+3, by+11, 4, 6+legSwing,  '#3A3A5A')
  px(ctx, bx+7, by+11, 4, 6-legSwing,  '#3A3A5A')

  // Body (shirt — agent color)
  px(ctx, bx+2, by+7,  10, 6, color)
  px(ctx, bx+1, by+7,  1,  4, color) // left arm
  px(ctx, bx+12,by+7,  1,  4, color) // right arm

  // Neck
  px(ctx, bx+5, by+5, 4, 3, P.skin)

  // Head (skin)
  px(ctx, bx+3, by,   8, 6, P.skin)

  // Hair / hat (darker version of agent color)
  px(ctx, bx+3, by,   8, 3, shadeColor(color, -40))

  // Eyes
  px(ctx, bx+4, by+3, 2, 2, '#222')
  px(ctx, bx+8, by+3, 2, 2, '#222')

  // State indicator (dot above head)
  const dotColor = STATE_COLOR[state] ?? STATE_COLOR.idle
  px(ctx, bx+11, by-3, 4, 4, '#111')
  px(ctx, bx+12, by-2, 2, 2, dotColor)

  // Thinking: animated dots
  if (state === 'thinking') {
    for (let i = 0; i < 3; i++) {
      const alpha = Math.sin(frame * 0.15 + i * 1.2) > 0 ? 1 : 0.3
      ctx.fillStyle = `rgba(241,196,15,${alpha})`
      ctx.fillRect(bx + 14 + i*5, by - 8, 3, 3)
    }
  }

  // Working: arm animation
  if (state === 'working') {
    const armY = by + 9 + Math.sin(frame * 0.3) * 1
    px(ctx, bx+1, armY, 2, 3, color)
  }
}

function drawSpeechBubble(ctx, x, y, text) {
  const w = Math.min(text.length * 5 + 10, 100)
  const h = 18
  const bx = x - w/2
  const by = y - 42

  // Bubble bg
  ctx.fillStyle = '#FAFAFA'
  ctx.strokeStyle = '#222'
  ctx.lineWidth = 1.5
  ctx.beginPath()
  ctx.roundRect(bx, by, w, h, 3)
  ctx.fill()
  ctx.stroke()

  // Tail
  ctx.fillStyle = '#FAFAFA'
  ctx.beginPath()
  ctx.moveTo(x-3, by+h); ctx.lineTo(x+3, by+h); ctx.lineTo(x, by+h+6)
  ctx.closePath(); ctx.fill()
  ctx.stroke()

  // Text
  ctx.fillStyle = '#111'
  ctx.font = `${Math.round(6/SCALE * SCALE)}px monospace`
  ctx.textAlign = 'center'
  ctx.fillText(text.slice(0,18), x, by + 12)
}

// ── Color utilities ───────────────────────────────────────────────────────────
function shadeColor(hex, amount) {
  const n = parseInt(hex.slice(1), 16)
  const r = Math.max(0, Math.min(255, (n >> 16) + amount))
  const g = Math.max(0, Math.min(255, ((n >> 8) & 0xff) + amount))
  const b = Math.max(0, Math.min(255, (n & 0xff) + amount))
  return `rgb(${r},${g},${b})`
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function OfficeCanvas({ agents, agentStates }) {
  const canvasRef      = useRef(null)
  const rafRef         = useRef(null)
  const frameRef       = useRef(0)
  const agentStatesRef = useRef(agentStates)
  agentStatesRef.current = agentStates   // always fresh, no loop restart

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !agents.length) return
    const ctx = canvas.getContext('2d')
    ctx.imageSmoothingEnabled = false

    const agentMap = Object.fromEntries(agents.map(a => [a.id, a]))

    function draw() {
      frameRef.current++
      const frame = frameRef.current
      ctx.clearRect(0, 0, VW, VH)

      // Background
      drawOfficeBackground(ctx)

      // Desks (drawn before characters so chars appear on top)
      Object.entries(LAYOUT).forEach(([id, {desk}]) => {
        drawDesk(ctx, desk, id === 'vp')
      })

      // Characters
      Object.entries(LAYOUT).forEach(([id, {stand}]) => {
        const agent = agentMap[id]
        if (!agent) return
        const st = agentStatesRef.current?.[id] ?? {}
        const state   = st.state   ?? 'idle'
        const message = st.message ?? ''
        const idleY   = stand.y + Math.sin(frame * 0.04 + id.length) * 0.8

        drawCharacter(ctx, stand.x, idleY, agent.color, state, frame, id)

        if (message && state !== 'idle' && state !== 'done') {
          drawSpeechBubble(ctx, stand.x, idleY, message)
        }
      })

      // Agent names (small label under each desk area)
      ctx.font = '5px monospace'
      ctx.textAlign = 'center'
      Object.entries(LAYOUT).forEach(([id, {desk, stand}]) => {
        const st = agentStatesRef.current?.[id] ?? {}
        ctx.fillStyle = STATE_COLOR[st.state ?? 'idle'] ?? '#888'
        ctx.fillText(LAYOUT[id].label, stand.x, stand.y + 8)
      })

      rafRef.current = requestAnimationFrame(draw)
    }

    draw()
    return () => cancelAnimationFrame(rafRef.current)
  }, [agents])  // solo reinicia si cambia la lista de agentes, no los estados

  return (
    <canvas
      ref={canvasRef}
      width={VW}
      height={VH}
      style={{
        width:  VW * SCALE,
        height: VH * SCALE,
        imageRendering: 'pixelated',
        display: 'block',
        maxWidth: '100%',
      }}
      className="pixel-border"
    />
  )
}
