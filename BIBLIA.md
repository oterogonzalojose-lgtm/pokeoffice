# BIBLIA DE POKEOFFICE
> Documento vivo. Actualizar SIEMPRE antes de mergear cualquier cambio significativo.
> Última actualización: 31/05/2026 — post code review, testing suite y fixes de robustez

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
| Memoria VP, Master DEV, Contador fallback | `claude-haiku-4-5-20251001` | Background, barato, suficiente |
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
- **Sheets**: Dos ContextVars en `sheets_client.py`: `_tenant_sid_ctx` (spreadsheet_id) y `_tenant_id_ctx` (tenant_id). Se setean en `run_vp()` al inicio de cada request.
- **Memoria VP**: `_HISTORY` keyed por `(tenant_id, user_email)`. Cada usuario tiene su hilo.
- **DB**: Todas las tablas operativas tienen `tenant_id`. Config usa PK compuesta `(clave, tenant_id)`.

### Background tasks
```python
# SIEMPRE usar _fire_and_track, NUNCA asyncio.create_task() suelto
# asyncio solo guarda weak refs — el GC elimina tasks sin referencia fuerte
_fire_and_track(coro)  # en vp.py — también usado en api.py para request_logs
```

### Sheets per-tenant
```python
# Al inicio de run_vp():
set_tenant_id_ctx(tenant_id)          # para escalar_problema del Programador
tenant_data = await get_tenant(tenant_id)
sid = (tenant_data or {}).get("spreadsheet_id") or ""  # or "" para cubrir None de SQLite
if sid:
    set_tenant_spreadsheet_id_ctx(sid)
```

### Credenciales Sheets — caché obligatorio
```python
@functools.lru_cache(maxsize=1)
def _creds(): ...   # parsea JSON de env var UNA sola vez

@functools.lru_cache(maxsize=1)
def _sheets(): ...  # construye cliente UNA sola vez

@functools.lru_cache(maxsize=1)
def _drive(): ...
```

### Auth
- JWT usuario: 30 días. Payload: `role=user`, `user_id`, `tenant_id`, `email`
- JWT admin: sin expiración. Invalidar cambiando `ADMIN_SECRET`.
- WebSocket valida `?token=` en query param al conectar.
- Middleware verifica tenant activo en DB en cada request.
- Diagnóstico admin: JWT Bearer (NO query param — cambio de seguridad).

---

## 5. STACK TÉCNICO

```
Backend:    Python 3.11, FastAPI, aiosqlite, PyJWT
Agentes:    Anthropic SDK — await call_with_retry() + safe_text() en todos los agentes
Frontend:   React 19, Vite, Tailwind CSS v4, HTML5 Canvas
Sheets:     Google Sheets API v4, Drive API v3 (service account — lru_cache en cliente)
Deploy:     Railway — Dockerfile, volumen /data, single uvicorn worker
DB:         SQLite en /data/pokeoffice.db
Tests:      pytest + pytest-asyncio, 36 tests de regresión
```

---

## 6. MAPA DE ARCHIVOS CLAVE

| Archivo | Responsabilidad |
|---|---|
| `backend/api.py` | FastAPI app, middlewares, WebSocket, endpoints usuario |
| `backend/agents/vp.py` | Orquestador VP. `_HISTORY`, `_bg_tasks`, `_fire_and_track`, `_es_confirmacion` (word-boundary) |
| `backend/agents/base.py` | BaseAgent: loop de tool_use, broadcast, `call_with_retry` |
| `backend/agents/utils.py` | `call_with_retry` (sync→async via executor), `safe_text`, constantes |
| `backend/agents/atencion_cliente.py` | Recepcionista: alta/búsqueda/actualización de clientes. `await call_with_retry()`. |
| `backend/agents/contador.py` | Contador: ingresos/egresos/balances. Valida monto > 0. `await call_with_retry()`. |
| `backend/agents/proveedores.py` | Proveedores: stock entrada/venta/corrección/precio |
| `backend/agents/programador.py` | Diagnóstico técnico. Usa `sh._sheets()`. Tool `escalar_problema`. |
| `backend/agents/memoria_vp.py` | Extracción post-conversación (Haiku). Strip markdown antes de json.loads. |
| `backend/agents/master_dev.py` | Análisis de errores en background → `platform_events` |
| `backend/mcp/sheets_client.py` | Todas las ops Sheets. ContextVars. `@lru_cache`. Columnas personalizadas. |
| `backend/db/models.py` | `init_db()`, CRUD operativo por tenant |
| `backend/db/admin_models.py` | CRUD cross-tenant para admin. `platform_events` con `respuesta_admin`. |
| `backend/admin_fixes.py` | Fixes globales ejecutables para todos los tenants desde el admin panel |
| `backend/routers/admin.py` | Endpoints `/api/admin/*`. Diagnóstico requiere JWT Bearer. |
| `backend/routers/auth.py` | `/auth/verificar`, `/auth/solicitar`, `/auth/me` |
| `frontend/src/App.jsx` | SPA principal, routing por estado |
| `frontend/src/components/AdminPanel.jsx` | Panel admin completo con todos los tabs |
| `frontend/src/hooks/useWebSocket.js` | WS con reconexión, token en URL |
| `frontend/src/utils/api.js` | `apiFetch`, `getToken`, `getWsUrl` |
| `tests/conftest.py` | Fixtures y mocks para pytest (Anthropic echo, Sheets mock) |
| `tests/test_regression.py` | 36 tests de regresión — todos los bugs fijados |
| `tests/scenarios/` | Seeding de 5 tenants + stress test de conversaciones |

---

## 7. ESQUEMA DE BASE DE DATOS

| Tabla | Campos clave | Notas |
|---|---|---|
| `tenants` | id, email, nombre_negocio, plan, activo, **spreadsheet_id** | `spreadsheet_id` puede ser NULL — usar `or ""` |
| `users` | id, tenant_id, email, nombre, activo, last_login | Máx 2 activos por tenant |
| `invitaciones` | id, tenant_id, email, codigo, usado, expires_at | 6 dígitos, 24h |
| `solicitudes_registro` | id, email, nombre, mensaje, atendida | Pública, sin auth |
| `conversations` | id, tenant_id, **user_email**, user_message, vp_response, events | events = JSON array |
| `vp_memoria` | id, tenant_id, **user_email**, tipo, aprendizaje, relevancia, usos | Keyed por (tenant, user) |
| `configuracion` | **(clave, tenant_id)** PK compuesta, valor | Migración de PK simple ya aplicada |
| `recordatorios` | id, tenant_id, texto, tipo, fecha, completado, origen | |
| `feedback` | id, tenant_id, mensaje, tipo, leido | |
| `platform_events` | id, tenant_id, tipo (fix\|mejora\|escalacion), titulo, descripcion, razonamiento, aplicabilidad, estado, **respuesta_admin** | respuesta_admin: decisión del admin ante una escalación |
| `request_logs` | id, created_at, tenant_id, user_email, method, path, status_code, duration_ms | Max 5000 entradas, auto-pruning |

---

## 8. AGENTES Y HERRAMIENTAS

### VP (Orquestador)
- **Modelo**: sonnet-4-6
- **Tools propias**: `briefing_cliente`, `agregar_columna_personalizada` (Clientes/Stock — Finanzas protegida)
- **Tools de delegación**: `delegar_atencion_cliente`, `delegar_contador`, `delegar_proveedores`, `delegar_marketing`, `delegar_programador`
- **Reglas críticas**:
  - Nunca exponer routing interno al jefe
  - **COMPRAS**: registrar_entrada_stock + egreso Contador en el MISMO turno
  - **VENTAS**: registrar_venta_stock + ingreso Contador + cliente nuevo (Recep) si aplica — SIEMPRE los tres
  - Info complementaria en turno siguiente = solo actualizar ese campo, nunca re-registrar
  - **CORRECCIONES**: `set_unidades_stock` (reemplaza), nunca nueva entrada
  - **ACTUALIZACIÓN CLIENTES**: formato exacto `"Actualizar [NOMBRE]: campo [X] = [Y]"`
  - `_es_confirmacion()` usa word-boundary (`\b`) — NO substring — para evitar falsos positivos

### Recepcionista (AtencionClienteAgent)
- Intent detection + `await call_with_retry()` para formateo final
- **Alta cliente**: dedup por nombre Y por teléfono antes de registrar
- **Actualización campos**: extrae pares `campo X = valor` con regex, soporta columnas custom
- **Búsqueda**: por nombre, apellido, teléfono, email
- Sheets: `agregar_cliente`, `buscar_cliente`, `listar_clientes`, `actualizar_campo_cliente`

### Contador (ContadorAgent)
- Intent detection + `await call_with_retry()` para formateo + clasificación fallback con Haiku
- **Valida monto > 0** antes de registrar — pide importe si no lo encuentra
- Dedup: mismo día + mismo monto + misma categoría → rechaza con "⚠ Movimiento duplicado"
- Sheets: `registrar_movimiento_finanzas`, `obtener_resumen_finanzas`, `actualizar_posicion_bancaria`

### Proveedores (ProveedoresAgent)
- `registrar_entrada_stock` — SUMA unidades. Solo para mercadería nueva físicamente recibida.
- `registrar_venta_stock` — RESTA unidades. Para ventas. Devuelve precio de venta al VP.
- `set_unidades_stock` — REEMPLAZA cantidad. Solo para correcciones de inventario.
- `actualizar_precio_stock` — Solo actualiza precio/costo/margen.
- `listar_stock`, `buscar_producto` (fuzzy por palabras individuales)
- **Regla**: SIEMPRE buscar antes de registrar. Si existe y es solo actualización → no sumar unidades.

### Programador (ProgramadorAgent)
- Usa `sh._sheets()` (respeta `GOOGLE_SERVICE_ACCOUNT_JSON` de Railway — NO credentials file)
- `verificar_planilla`, `listar_hojas`
- `escalar_problema`: guarda platform_event tipo "escalacion" via sqlite3 síncrono + `_tenant_id_ctx`
- El admin ve la escalación en el panel y puede responder con `PATCH /platform-events/:id/responder`

### Marketing (MarketingAgent)
- Sin tools de sheets. Solo generación de contenido con Claude.

### Master DEV (background)
- Modelo: Haiku
- Se activa cuando VP responde con "dificultad técnica"
- Genera fix/mejora en `platform_events`
- Nunca visible al cliente

---

## 9. ANTI-PATRONES CONOCIDOS (NO REPETIR)

| Anti-patrón | Por qué falla | Fix correcto |
|---|---|---|
| `asyncio.create_task(coro)` sin referencia | GC elimina el task antes de terminar | `_fire_and_track(coro)` |
| `dict.get("key", "")` cuando SQLite devuelve NULL | `get` respeta el valor None, no aplica default | `dict.get("key") or ""` |
| Sync `_client.messages.create()` en async | Bloquea event loop durante toda la llamada de red | `await call_with_retry(_client.messages.create, ...)` |
| `listar_tenants()` para leer `spreadsheet_id` | La query no incluye esa columna | `get_tenant(tid)` que hace `SELECT *` |
| Triple-quote con chars Unicode (═══) fuera del string | SyntaxError en import | Evitar esos chars en strings Python |
| `asyncio.get_event_loop()` en Python 3.10+ | DeprecationWarning, puede fallar | `asyncio.get_running_loop()` |
| `buscar_producto` con substring completo | "platitos" no matchea "platito" | Tokenizar por palabras (`split()`) |
| `_apply_formats(svc, sid)` llama `_sheets()` internamente | Ignora svc recibido, crea cliente nuevo (doble auth, doble costo) | `svc.spreadsheets().get(...)` |
| `_creds()` / `_sheets()` / `_drive()` sin caché | Parsea JSON y crea cliente en cada request | `@functools.lru_cache(maxsize=1)` |
| `_es_confirmacion()` con `any(w in m for w in _CONF)` | "sistema" matchea "si" — falso positivo | `re.search(r'\b' + re.escape(w) + r'\b', m)` |
| `json.loads(raw)` sin strip de markdown | Claude devuelve ```json ... ``` → JSONDecodeError | Strip de backtick-block antes de `json.loads` |
| Registrar movimiento financiero sin validar monto | `_extraer_monto()` devuelve 0.0 → registro de $0 | `if not monto: return "Indicá el importe"` |
| Funciones síncronas de Sheets en async admin | Bloquea uvicorn durante llamadas de red en admin_fixes | `await asyncio.to_thread(fix_func, tenant)` |
| Password en query param (`?pw=`) | Visible en logs de Railway y browser history | JWT Bearer como el resto del admin |
| Regex `[A-ZÁÉÍÓÚÑ]` con `re.IGNORECASE` para nombres | Matchea "con" y "los" como nombres propios | Sin IGNORECASE + prioridad a etiqueta `Nombre:` |
| Monto extractor captura años como monto | `\b\d{4}\b` en fallback matchea "2025" → $2025 | Filtro de contexto + prioridad a `$` en el texto |

---

## 10. API ENDPOINTS

### Usuario (require JWT user)
| Endpoint | Descripción |
|---|---|
| `POST /auth/verificar` | Verificar código → JWT (público) |
| `POST /message` | Instrucción al VP |
| `GET /history` | Historial de conversaciones |
| `GET /recordatorios` | Post-its del tenant |
| `POST /recordatorios` | Crear post-it |
| `GET /config` | Config del negocio |
| `POST /config/onboarding` | Guardar onboarding |
| `GET /planilla` | Info planilla del tenant |
| `POST /planilla/vincular` | Vincular sheet |
| `POST /planilla/actualizar-formulas` | Actualizar fórmulas (setea ContextVar correctamente) |
| `GET /dashboard` | KPIs financieros (ContextVar fix aplicado) |
| `WS /ws?token=` | WebSocket aislado por tenant |

### Admin (require JWT Bearer)
| Endpoint | Descripción |
|---|---|
| `GET /api/admin/tenants` | Lista tenants (sin spreadsheet_id — usar GET :id) |
| `POST /api/admin/tenants` | Crear tenant |
| `GET /api/admin/tenants/:id` | Detalle completo con spreadsheet_id |
| `POST /api/admin/tenants/:id/invite` | Código 6 dígitos, 24h |
| `POST /api/admin/tenants/:id/vincular-planilla` | Linkear sheet |
| `POST /api/admin/tenants/:id/crear-planilla` | Crear sheet nuevo (requiere Drive quota disponible) |
| `GET /api/admin/tenants/:id/memoria` | VP Memoria |
| `GET /api/admin/logs` | Request logs |
| `GET /api/admin/platform-events` | Eventos Master DEV — ?tipo=fix\|mejora\|escalacion&estado= |
| `PATCH /api/admin/platform-events/:id/estado` | Cambiar estado del evento |
| `PATCH /api/admin/platform-events/:id/responder` | Admin responde escalación (guarda respuesta_admin) |
| `GET /api/admin/fixes` | Lista fixes ejecutables para todos los tenants |
| `POST /api/admin/fixes/:fix_id` | Ejecutar fix para todos los tenants |
| `GET /api/admin/diagnostico` | Diagnóstico del sistema (JWT Bearer — NO ?pw=) |

---

## 11. VARIABLES DE ENTORNO RAILWAY

| Variable | Descripción |
|---|---|
| `ANTHROPIC_API_KEY` | Clave Anthropic |
| `ADMIN_PASSWORD` | Password del panel /admin |
| `ADMIN_SECRET` | Secret JWT admin (recomendado ≥32 chars) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON completo de la service account |
| `DATA_DIR` | Seteado en Dockerfile como `/data` |

**Service account**: `pokeoffice-agent@pokeoffice.iam.gserviceaccount.com`
**Nota Drive quota**: si la quota de la service account está llena, `crear-planilla` falla (403). Alternativa: el cliente crea la hoja en su Drive y usa `vincular-planilla`.

---

## 12. PENDIENTES ACTIVOS

- [x] `get_dashboard_data()` — RESUELTO: GET /dashboard ahora setea ContextVar antes de llamar a Sheets.
- [x] 10 bugs del code review — RESUELTOS: sync Anthropic, $0 sin monto, _apply_formats, GC task, _es_confirmacion, lru_cache, json.loads markdown, asyncio.to_thread, password query param, /planilla sin auth.
- [ ] Resend: envío automático de códigos de invitación por email.
- [ ] Drive quota: service account llena — considerar migrar a creación de hojas por el propio cliente.
- [ ] Stress test completo: vincular 5 hojas a los tenants de testing y re-correr `stress_test.py` con datos reales.
- [ ] Alerta de stock: `job_alerta_stock()` es un TODO sin implementar.
- [ ] WhatsApp / Email para mensajes reales a clientes del emprendedor.
- [ ] PDF de reportes contables.

---

## 13. CHECKLIST PRE-COMMIT

Antes de hacer push, verificar:
- [ ] `python -c "import ast; ast.parse(open('archivo.py').read())"` en archivos Python modificados
- [ ] `pytest tests/ -v` — deben pasar los 36 tests de regresión
- [ ] Strings de triple-quote bien cerrados
- [ ] Ningún `asyncio.create_task()` suelto → usar `_fire_and_track()`
- [ ] Ningún `_client.messages.create()` síncrono → usar `await call_with_retry()`
- [ ] Si se modifica DB: ¿hay migración `ALTER TABLE` en `init_db()`?
- [ ] Si se agrega tool a un agente: ¿está en `tools()` Y en `execute_tool()`?
- [ ] Si se toca `listar_tenants()`: recordar que NO devuelve `spreadsheet_id`
- [ ] Build frontend si se modificó AdminPanel: `npm run build`
- [ ] Si se agrega endpoint: ¿está documentado en BIBLIA, Notion y tab Docs del admin?
