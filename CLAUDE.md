# CLAUDE.md — Pokeoffice

Plataforma multi-agente con estética pixel art para emprendedores y pequeños negocios.

## Concepto

El usuario da instrucciones en lenguaje natural (como hablaría con un empleado real) y los agentes IA actúan en consecuencia. Un **VP orquestador** recibe las órdenes, delega a agentes especializados, y todo se visualiza en una oficina pixel art interactiva.

## Agentes

| ID | Nombre | Rol |
|----|--------|-----|
| `vp` | VP / Jefe de Gabinete | Orquestador. Recibe instrucciones del jefe (humano), delega, supervisa |
| `atencion_cliente` | Recepcionista | Turnos, consultas, respuestas a clientes |
| `contador` | Contador | Facturación, gastos, balances |
| `proveedores` | Gestor de Proveedores | Órdenes de compra, cotizaciones |
| `rrhh` | RRHH / Legal | Contratos, liquidaciones, normativa |
| `marketing` | Marketing | Comunicaciones, redes, promociones |

## Comandos

### Backend (Python/FastAPI)
```bash
cd pokeoffice/backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

### Frontend (React + Vite + PixiJS)
```bash
cd pokeoffice/frontend
npm install
npm run dev     # dev server en :5173
npm run build   # build → dist/
```

### Variables de entorno
Copiar `.env.example` a `.env` y completar:
```
ANTHROPIC_API_KEY=sk-...
GOOGLE_DRIVE_CREDENTIALS=...  # JSON de service account
```

## Arquitectura

```
pokeoffice/
├── backend/
│   ├── api.py              # FastAPI + WebSocket + APScheduler
│   ├── agents/
│   │   ├── base.py         # BaseAgent: state machine + broadcast
│   │   ├── vp.py           # VP: orchestrator con tool_use
│   │   ├── atencion_cliente.py
│   │   ├── contador.py
│   │   ├── proveedores.py
│   │   ├── rrhh.py
│   │   └── marketing.py
│   ├── mcp/
│   │   └── drive_client.py # Google Drive MCP wrapper
│   └── db/
│       └── models.py       # SQLite: conversaciones + config agentes
└── frontend/
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── OfficeCanvas.jsx  # PixiJS: oficina pixel art
        │   ├── ChatInput.jsx     # Input para instrucciones al VP
        │   └── ActivityFeed.jsx  # Feed de eventos de agentes
        └── hooks/
            └── useWebSocket.js   # WebSocket → eventos de agentes
```

### Flujo de datos
1. Usuario escribe instrucción → `POST /message`
2. VP recibe → analiza → llama tools (delegar_agente) via Claude tool_use
3. Cada tool call emite evento WebSocket `{type, agent, state, message}`
4. El agente destino corre, emite sus propios eventos, devuelve resultado
5. VP sintetiza → respuesta final via WebSocket
6. Frontend anima sprites en tiempo real según los eventos

### WebSocket events
```json
{"type": "agent_state", "agent": "contador", "state": "thinking", "message": "..."}
{"type": "agent_message", "from": "vp", "to": "contador", "message": "..."}
{"type": "vp_response", "message": "Resultado final para el usuario"}
{"type": "error", "message": "..."}
```

## Stack
- **Backend**: Python 3.11+, FastAPI, Anthropic SDK, aiosqlite
- **Frontend**: React 19, Vite, PixiJS 8, Tailwind CSS v4
- **IA**: claude-sonnet-4-6 (VP + agentes)
- **MCP**: Google Drive
- **Deploy**: Railway
