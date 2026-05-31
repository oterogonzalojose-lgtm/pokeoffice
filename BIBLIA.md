# BIBLIA DE POKEOFFICE
> Documento vivo. Actualizar SIEMPRE antes de mergear cualquier cambio significativo.
> Última actualización: 31/05/2026

---

## 1. METODOLOGÍA DE TRABAJO OBLIGATORIA

Antes de proponer cualquier solución, el asistente debe activar los 4 roles y dialogar entre ellos:

### Rol 1 — Arquitecto de Datos
- ¿Cómo impacta esto en el esquema de DB?
- ¿Hay riesgo de duplicados, pérdida de datos, migración rota?
- ¿El modelo es multi-tenant seguro?

### Rol 2 — Programador Experto
- ¿Hay riesgo de SyntaxError, import circular, GC de tasks async?
- ¿El cambio es compatible con el event loop de uvicorn?
- ¿Estoy modificando solo lo necesario o estoy sobreingeniería?

### Rol 3 — Prompt Engineer
- ¿El system prompt tiene ambigüedad que el LLM puede malinterpretar?
- ¿Las reglas son mutuamente excluyentes y MECE?
- ¿Estoy usando tokens de manera eficiente?

### Rol 4 — CFO (presupuesto ajustado)
- ¿Qué modelo uso? Regla: Haiku para background, Sonnet para agentes principales.
- ¿Cuántos tokens consume este cambio por request?
- ¿Puedo lograr lo mismo con menos llamadas a la API?

### Diálogo entre roles → decisión
Solo después de este análisis se propone la solución. La prioridad siempre es:
**Confiabilidad > Costo > Velocidad de implementación**

---

## 2. VISIÓN DEL PRODUCTO

**Qué es:** SaaS multi-tenant plug & play. Una "mini oficina" de agentes IA para emprendedores.
**Promesa core:** Se siente como empleados reales, no como un chatbot.
**Invariante absoluta:** Todos los tenants corren el mismo código. Zero customizaciones por tenant.
**Target:** Pequeños negocios / emprendedores. Precio accesible.

---

## 3. MODELO DE COSTOS (CFO)

| Uso | Modelo | Justificación |
|---|---|---|
| VP + Agentes (conversación) | `claude-sonnet-4-6` | Calidad necesaria para business logic |
| Memoria VP, Master DEV | `claude-haiku-4-5-20251001` | Background, barato, suficiente |
| Nunca usar | Opus | Solo si el usuario lo pide explícitamente |

**Reglas de ahorro de tokens:**
- System prompts: concisos, sin repetición. Máximo ~500 tokens por agente.
- Historial VP: máximo 40 mensajes por sesión (`MAX_HISTORY = 40`). Se trim automáticamente.
- Memoria: máximo 25 aprendizajes en contexto (`limit=25` en `obtener_memoria`).
- Background tasks: fire-and-forget con `_fire_and_track()`. No bloquean respuesta.
- Max 2 aprendizajes extraídos por conversación (regla en extraction prompt).

---

## 4. ARQUITECTURA — INVARIANTES

### Multi-tenancy
- **WebSocket**: `ConnectionManager` keyed por `tenant_id`. Broadcast solo al tenant activo.
- **Sheets**: `ContextVar` `_tenant_sid_ctx` en `sheets_client.py`. Se setea en `run_vp()` al inicio de cada request con el `spreadsheet_id` del tenant desde DB.
- **Memoria VP**: `_HISTORY` keyed por `(tenant_id, user_email)`. Cada usuario tiene su hilo.
- **DB**: Todas las tablas operativas tienen `tenant_id`. Config usa PK compuesta `(clave, tenant_id)`.

### Background tasks
```python
# SIEMPRE usar _fire_and_track, NUNCA asyncio.create_task() suelto
# asyncio solo guarda weak refs — el GC elimina tasks sin referencia fuerte
_fire_and_track(coro)  # en vp.py
```

### Sheets per-tenant
```python
# Al inicio de run_vp():
tenant_data = await get_tenant(tenant_id)
sid = (tenant_data or {}).get("spreadsheet_id") or ""  # or "" para cubrir None de SQLite
if sid:
    set_tenant_spreadsheet_id_ctx(sid)
```

### Auth
- JWT usuario: 30 días. Payload: `role=user`, `user_id`, `tenant_id`, `email`
- JWT admin: sin expiración. Invalidar cambiando `ADMIN_SECRET`.
- WebSocket valida `?token=` en query param al conectar.
- Middleware verifica tenant activo en DB en cada request.

---

## 5. STACK TÉCNICO

```
Backend:    Python 3.11, FastAPI, aiosqlite, PyJWT
Agentes:    Anthropic SDK (sync client + call_with_retry en executor)
Frontend:   React 19, Vite, Tailwind CSS v4, HTML5 Canvas
Sheets:     Google Sheets API v4, Drive API v3 (service account)
Deploy:     Railway — Dockerfile, volumen /data, single uvicorn worker
DB:         SQLite en /data/pokeoffice.db
```

---

## 6. MAPA DE ARCHIVOS CLAVE

| Archivo | Responsabilidad |
|---|---|
| `backend/api.py` | FastAPI app, middlewares, WebSocket, endpoints usuario |
| `backend/agents/vp.py` | Orquestador VP. `_HISTORY`, `_bg_tasks`, `_fire_and_track` |
| `backend/agents/base.py` | BaseAgent: loop de tool_use, broadcast, `call_with_retry` |
| `backend/agents/utils.py` | `call_with_retry` (sync→async via executor), constantes |
| `backend/agents/memoria_vp.py` | Extracción de aprendizajes post-conversación (Haiku) |
| `backend/agents/master_dev.py` | Análisis de errores en background → `platform_events` |
| `backend/mcp/sheets_client.py` | Todas las operaciones de Google Sheets. ContextVar aquí. |
| `backend/db/models.py` | `init_db()`, CRUD operativo por tenant |
| `backend/db/admin_models.py` | CRUD cross-tenant para admin. `init_feedback_table()` |
| `backend/routers/admin.py` | Todos los endpoints `/api/admin/*` |
| `backend/routers/auth.py` | Login, verificación de código, JWT de usuario |
| `frontend/src/App.jsx` | SPA principal, routing por estado |
| `frontend/src/components/AdminPanel.jsx` | Panel admin completo |
| `frontend/src/hooks/useWebSocket.js` | WS con reconexión, token en URL |
| `frontend/src/utils/api.js` | `apiFetch`, `getToken`, `getWsUrl` |

---

## 7. ESQUEMA DE BASE DE DATOS

| Tabla | Campos clave | Notas |
|---|---|---|
| `tenants` | id, email, nombre_negocio, plan, activo, **spreadsheet_id** | `spreadsheet_id` puede ser NULL |
| `users` | id, tenant_id, email, nombre, activo, last_login | Máx 2 activos por tenant |
| `invitaciones` | id, tenant_id, email, codigo, usado, expires_at | 6 dígitos, 24h |
| `solicitudes_registro` | id, email, nombre, mensaje, atendida | Pública, sin auth |
| `conversations` | id, tenant_id, **user_email**, user_message, vp_response, events | events = JSON array |
| `vp_memoria` | id, tenant_id, **user_email**, tipo, aprendizaje, relevancia, usos | Keyed por (tenant, user) |
| `configuracion` | **(clave, tenant_id)** PK compuesta, valor | Migración de PK simple ya aplicada |
| `recordatorios` | id, tenant_id, texto, tipo, fecha, completado, origen | |
| `feedback` | id, tenant_id, mensaje, tipo, leido | |
| `platform_events` | id, tenant_id, tipo, titulo, descripcion, razonamiento, aplicabilidad, estado | Master DEV |
| `request_logs` | id, created_at, tenant_id, user_email, method, path, status_code, duration_ms | Max 5000 entradas |

---

## 8. AGENTES Y HERRAMIENTAS

### VP (Orquestador)
- **Modelo**: sonnet-4-6
- **Tools propias**: `briefing_cliente`
- **Tools de delegación**: `delegar_atencion_cliente`, `delegar_contador`, `delegar_proveedores`, `delegar_marketing`, `delegar_programador`
- **Reglas críticas**:
  - Nunca exponer routing interno al jefe
  - Compra de stock = registrar stock + egreso en el MISMO turno
  - Info complementaria (proveedor) en turno siguiente = solo actualizar ese campo
  - Correcciones = `set_unidades_stock`, nunca nueva entrada

### Recepcionista (AtencionClienteAgent)
- `agregar_cliente`, `listar_clientes`, `buscar_cliente`

### Contador (ContadorAgent)
- `registrar_movimiento_finanzas`, `listar_movimientos`, `obtener_saldo`
- Dedup: si el último movimiento del día tiene mismo monto+categoría → rechaza con "⚠ Movimiento duplicado"

### Proveedores (ProveedoresAgent)
- `registrar_entrada_stock` — SUMA unidades. Solo para mercadería nueva que físicamente llegó.
- `set_unidades_stock` — REEMPLAZA cantidad. Solo para correcciones.
- `actualizar_precio_stock` — Solo actualiza precio/costo/margen.
- `listar_stock`, `buscar_producto` (fuzzy por palabras)
- **Regla**: SIEMPRE buscar antes de registrar. Si existe y es solo actualización de datos → no sumar unidades.

### Marketing (MarketingAgent)
- Sin tools de sheets. Solo generación de contenido con Claude.

### Programador (ProgramadorAgent)
- Diagnóstico de errores técnicos internos. Nunca visible al cliente.

---

## 9. ANTI-PATRONES CONOCIDOS (NO REPETIR)

| Anti-patrón | Por qué falla | Fix correcto |
|---|---|---|
| `asyncio.create_task(coro)` sin referencia | GC elimina el task antes de terminar | `_fire_and_track(coro)` |
| `dict.get("key", "")` cuando SQLite devuelve NULL | `get` respeta el valor None, no aplica default | `dict.get("key") or ""` |
| Sync `_client.messages.create()` en async | Bloquea event loop | `await call_with_retry(_client.messages.create, ...)` |
| `listar_tenants()` para leer `spreadsheet_id` | La query no incluye esa columna | `get_tenant(tid)` que hace `SELECT *` |
| Triple-quote con chars Unicode (═══) fuera del string | SyntaxError en import | Evitar esos chars en strings Python |
| `asyncio.get_event_loop()` en Python 3.10+ | DeprecationWarning, puede fallar | `asyncio.get_running_loop()` |
| `buscar_producto` con substring completo | "platitos" no matchea "platito" | Tokenizar por palabras (`split()`) |
| Registrar `request_logs` sin try-except en middleware | Un error de DB rompe la respuesta | Wrapped en try-except, fire-and-forget |

---

## 10. API ENDPOINTS

### Usuario (require JWT user)
| Endpoint | Descripción |
|---|---|
| `POST /message` | Instrucción al VP |
| `GET /history` | Historial de conversaciones |
| `GET /recordatorios` | Post-its del tenant |
| `POST /recordatorios` | Crear post-it |
| `GET /config` | Config del negocio |
| `POST /config/onboarding` | Guardar onboarding |
| `GET /planilla` | Info planilla del tenant |
| `POST /planilla/vincular` | Vincular sheet |
| `GET /dashboard` | KPIs financieros |
| `WS /ws?token=` | WebSocket aislado por tenant |

### Admin (require JWT admin)
| Endpoint | Descripción |
|---|---|
| `GET /api/admin/tenants` | Lista tenants (sin spreadsheet_id — usar GET /tenants/:id) |
| `POST /api/admin/tenants` | Crear tenant |
| `GET /api/admin/tenants/:id` | Detalle completo con spreadsheet_id |
| `POST /api/admin/tenants/:id/invite` | Código 6 dígitos, 24h |
| `POST /api/admin/tenants/:id/vincular-planilla` | Linkear sheet |
| `GET /api/admin/tenants/:id/memoria` | VP Memoria |
| `GET /api/admin/logs` | Request logs |
| `GET /api/admin/platform-events` | Eventos Master DEV |
| `GET /api/admin/diagnostico?pw=` | Diagnóstico del sistema |

---

## 11. VARIABLES DE ENTORNO RAILWAY

| Variable | Descripción |
|---|---|
| `ANTHROPIC_API_KEY` | Clave Anthropic |
| `ADMIN_PASSWORD` | Password del panel /admin |
| `ADMIN_SECRET` | Secret JWT admin (recomendado ≥32 chars) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON completo de la service account |
| `DATA_DIR` | Seteado en Dockerfile como `/data` |

---

## 12. PENDIENTES ACTIVOS

- [x] `get_dashboard_data()` — RESUELTO: GET /dashboard ahora setea ContextVar antes de llamar a Sheets.
- [ ] Resend: envío automático de códigos de invitación por email.
- [ ] Alerta de stock: `job_alerta_stock()` es un TODO sin implementar.
- [ ] WhatsApp / Email para mensajes reales a clientes del emprendedor.
- [ ] PDF de reportes contables.
- [ ] El Programador (Dev agent) no siempre tiene el ContextVar cuando verifica la planilla.

---

## 13. CHECKLIST PRE-COMMIT

Antes de hacer push, verificar:
- [ ] `python -c "import ast; ast.parse(open('archivo.py').read())"` en archivos Python modificados
- [ ] Strings de triple-quote bien cerrados
- [ ] Ningún `asyncio.create_task()` suelto → usar `_fire_and_track()`
- [ ] Si se modifica DB: ¿hay migración `ALTER TABLE` en `init_db()`?
- [ ] Si se agrega tool a un agente: ¿está en `tools()` Y en `execute_tool()`?
- [ ] Si se toca `listar_tenants()`: recordar que NO devuelve `spreadsheet_id`
- [ ] Build frontend si se modificó AdminPanel: `npm run build`
