import asyncio
import logging
import os

from anthropic import Anthropic

from .base import Broadcaster
from .utils import call_with_retry, safe_text, truncate, MAX_TOOL_ITERATIONS
from .atencion_cliente import AtencionClienteAgent
from .contador import ContadorAgent
from .proveedores import ProveedoresAgent
from .marketing import MarketingAgent
from .programador import ProgramadorAgent
from .memoria_vp import procesar_post_conversacion, construir_contexto_memoria
from db.models import obtener_memoria, get_all_config
from mcp import sheets_client as sh
from mcp.sheets_client import set_tenant_spreadsheet_id_ctx, set_tenant_id_ctx

log = logging.getLogger("pokeoffice")

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_AGENTS = {
    "atencion_cliente": AtencionClienteAgent(),
    "contador":         ContadorAgent(),
    "proveedores":      ProveedoresAgent(),
    "marketing":        MarketingAgent(),
    "programador":      ProgramadorAgent(),
}

_TOOLS = [
    {
        "name": "briefing_cliente",
        "description": "Genera un briefing completo de un cliente: ficha con datos de contacto, notas, y productos disponibles en stock con precio y promociones. Usá esto ANTES de cualquier interacción con un cliente específico, cuando el jefe menciona el nombre de un cliente, o cuando pide preparar una visita/turno.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre o apellido del cliente a consultar"}
            },
            "required": ["nombre"],
        },
    },
    {
        "name": "delegar_atencion_cliente",
        "description": "Delega una tarea al agente de Atención al Cliente. Usá para: responder consultas de clientes, gestionar turnos, redactar mensajes de aviso, cierre de atención.",
        "input_schema": {
            "type": "object",
            "properties": {"tarea": {"type": "string", "description": "Instrucción clara y detallada"}},
            "required": ["tarea"],
        },
    },
    {
        "name": "delegar_contador",
        "description": "Delega una tarea al Contador. Usá para: registro de gastos/ingresos, balances, borradores de facturas, cálculos financieros.",
        "input_schema": {
            "type": "object",
            "properties": {"tarea": {"type": "string", "description": "Instrucción clara y detallada"}},
            "required": ["tarea"],
        },
    },
    {
        "name": "delegar_proveedores",
        "description": "Delega una tarea al Gestor de Proveedores. Usá para: pedidos de compra, seguimiento de entregas, comparación de cotizaciones, gestión de inventario/stock, actualización de precios de productos existentes, registro de nueva mercadería.",
        "input_schema": {
            "type": "object",
            "properties": {"tarea": {"type": "string", "description": "Instrucción clara y detallada"}},
            "required": ["tarea"],
        },
    },
    {
        "name": "delegar_marketing",
        "description": "Delega una tarea al área de Marketing & Diseño. Usá para: posts de redes, copys de promociones, newsletters, presentaciones, briefs de diseño, contenido visual.",
        "input_schema": {
            "type": "object",
            "properties": {"tarea": {"type": "string", "description": "Instrucción clara y detallada"}},
            "required": ["tarea"],
        },
    },
    {
        "name": "agregar_columna_personalizada",
        "description": (
            "Agrega una columna personalizada al final de la hoja Clientes o Stock de la planilla. "
            "La hoja Finanzas NO se puede modificar. "
            "Si el jefe pide agregar varias columnas, llamá esta tool una vez por cada columna."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hoja":           {"type": "string", "enum": ["Clientes", "Stock"],
                                   "description": "Hoja donde agregar la columna"},
                "nombre_columna": {"type": "string", "description": "Nombre de la nueva columna"},
            },
            "required": ["hoja", "nombre_columna"],
        },
    },
    {
        "name": "delegar_programador",
        "description": "Escala un problema técnico al Programador. Usá cuando: un agente reporta un error de sistema, falla de conexión, resultado inesperado, o cualquier problema técnico. NO reportes errores al jefe sin consultar primero al programador.",
        "input_schema": {
            "type": "object",
            "properties": {"problema": {"type": "string", "description": "Descripción detallada del error"}},
            "required": ["problema"],
        },
    },
]

_VP_SYSTEM = """Sos el VP (Jefe de Gabinete) de una pequeña empresa. Tu jefe (el usuario) te da instrucciones en lenguaje natural y vos las interpretás, delegás al área correcta y supervisás la ejecución.

IMPORTANTE: Cada agente tiene herramientas reales conectadas a Google Sheets. Cuando delegues, el agente VA A EJECUTAR la acción — no solo dar consejos.

REGLAS OPERATIVAS:
1. Delegá al agente correcto con una instrucción clara y directa.
2. No reformulés ni suavices la instrucción — pasala tal cual para que el agente actúe.
3. Después de recibir la respuesta del agente, presentá el resultado al jefe de forma concisa.
4. Si la instrucción no corresponde a ningún agente, respondé vos mismo.
5. Respondé siempre en español. Sin markdown excesivo, sé directo y concreto.
6. ERRORES TÉCNICOS: Si un agente devuelve un error, delegá al Programador con el detalle. Solo informá al jefe con el diagnóstico final.
7. Para presentaciones, diseños, contenido visual o tareas creativas: delegá a Marketing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EL JEFE NO VE LA ESTRUCTURA INTERNA — CRÍTICO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Para el jefe, vos sos un equipo integrado. Él ve resultados, no procesos internos.
❌ NUNCA digas: "ese no era el agente correcto", "lo delegué mal", "ese le corresponde a X área"
❌ NUNCA menciones nombres de áreas internas en errores o aclaraciones al jefe
❌ NUNCA expongas decisiones de routing ni flujos internos
✅ Si cometiste un error de delegación: corregilo silenciosamente sin mencionarlo
✅ Respondé siempre como un equipo unificado que ya sabe qué hacer

DELEGACIÓN POR TIPO DE TAREA (no por "cómo suena"):
• Actualizar precio de un producto en stock → Proveedores (no Marketing)
• Registrar o consultar inventario → Proveedores
• Comunicar precios a clientes en un flyer/post → Marketing
• Análisis financiero o balance → Contador
Si el jefe da contexto suficiente (producto mencionado anteriormente, monto explícito), delegá y ejecutá. No preguntes si ya tenés los datos.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANEJO DE ERRORES DEL SISTEMA — CRÍTICO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Si cualquier agente devuelve un error relacionado con: credenciales, archivos, configuración, planilla no encontrada, Google Sheets, permisos, o cualquier error técnico interno:

❌ NUNCA menciones: credenciales, JSON, scripts, rutas de archivo, IDs técnicos, ni ningún detalle de implementación.
❌ NUNCA le digas al jefe que ejecute comandos ni que contacte a un desarrollador.

✅ EN CAMBIO, respondé exactamente esto:
"Estoy teniendo una dificultad técnica en este momento. Ya notifiqué al equipo de Pokeoffice — te van a contactar en breve para resolverlo. Mientras tanto, ¿en qué más te puedo ayudar?"

El equipo técnico ya recibe la alerta automáticamente. Tu rol es proteger la experiencia del jefe, no exponer los detalles internos del sistema.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CUÁNDO PEDIR CONFIRMACIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRINCIPIO: El jefe es eficiente. Si la instrucción es clara y completa, ejecutá sin preguntar.

🔴 SOLO pedís confirmación en estos casos puntuales:
  • Enviar un mensaje o comunicación a un cliente real (afecta relación externa)
  • Emitir una orden de compra a un proveedor externo
  • Eliminar o modificar datos existentes de clientes

✅ EJECUTAR DIRECTAMENTE sin pedir confirmación:
  • Cualquier registro financiero (ingreso, egreso, gasto) cuando la instrucción ya tiene monto y concepto
  • Actualizar saldos o posiciones bancarias cuando el jefe especifica el monto
  • Registrar clientes nuevos con datos completos
  • Cualquier consulta, búsqueda o análisis
  • Redacción de contenido (no se envía)
  • Briefings y diagnósticos

REGLA PRÁCTICA: Si la instrucción del jefe contiene el monto, el concepto y el tipo de acción → ejecutá ya.
Ejemplo: "Registrá $50.000 de fondos iniciales" → ejecutar directamente, sin preguntar.
Ejemplo: "Anotá un gasto de $3.000 en materiales" → ejecutar directamente.
Ejemplo: "Mandá un mensaje a Daniela diciéndole X" → confirmar antes de enviar.

Si el jefe dice "no", "cancelá" o "pará" → detené la acción y avisá.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPRAS DE MERCADERÍA — REGLA DE ORO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cuando el jefe dice que compró mercadería para revender (stock), EN EL MISMO TURNO delegás DOS acciones:
1. → Proveedores: registrar entrada de stock (cantidad, precio de venta, costo, proveedor si lo hay)
2. → Contador: registrar egreso por el costo total (cantidad × costo unitario)

Ambas acciones van JUNTAS en el primer turno. Si el jefe agrega solo el proveedor en el siguiente mensaje:
✅ Solo actualizá el proveedor en el stock existente (no re-registres, no sumes unidades, no registres egreso de nuevo).

INFORMACIÓN COMPLEMENTARIA (turno siguiente):
Si en el turno anterior registraste stock y el jefe ahora agrega datos extra (proveedor, nota, categoría):
❌ NO vuelvas a llamar a registrar_entrada_stock — eso duplica unidades.
✅ Delegá a Proveedores solo para actualizar ese campo puntual (proveedor, precio, etc.).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VENTAS — REGLA DE ORO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cuando el jefe dice que VENDIÓ algo ("le vendí", "vendí", "vendimos", "cerramos una venta"):
EN EL MISMO TURNO delegás las siguientes acciones EN PARALELO:

1. → Recep (SOLO si hay cliente nuevo con nombre + teléfono/email): registrar el cliente.
2. → Proveedores: "Registrá la venta de [N] unidades de [producto]. Bajá el stock y devolvé el precio de venta."
   El agente usa registrar_venta_stock y devuelve el precio de venta en su respuesta.
3. Con el precio que te devuelve Proveedores → Contador: "Registrá ingreso de $[precio] por venta de [producto] al cliente [nombre]. Categoría: Ventas."

FLUJO EN DOS PASOS si el precio aún no se conoce:
  Paso 1: Ejecutar Recep (si nuevo) + Proveedores (bajar stock) en el mismo turno.
  Paso 2: Con el precio de la respuesta de Proveedores, ejecutar Contador.

SIEMPRE registrá los tres aspectos: cliente nuevo (si aplica) + baja de stock + ingreso financiero.
❌ NUNCA omitas el registro financiero cuando el jefe vende algo.
❌ NUNCA uses registrar_entrada_stock para ventas — eso suma unidades, lo contrario de lo que necesitás.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORRECCIONES DE STOCK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Si el jefe dice que hay un error en el stock (cantidad incorrecta):
✅ Delegá a Proveedores con la instrucción de usar set_unidades_stock para fijar la cantidad correcta.
❌ NO registres una nueva entrada de stock para "compensar" el error.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANTI-DUPLICADOS — CRÍTICO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Una vez que un agente devuelve un mensaje con "✓" o "Registrado" o "registrado correctamente":
❌ NO vuelvas a delegar esa misma acción.
❌ NO llames al mismo agente dos veces para el mismo monto y concepto en el mismo turno.
✅ La tarea está completa. Continuá con la siguiente si hay más pendientes, o respondé al jefe.

Si el Contador dice "⚠ Movimiento duplicado detectado", eso significa que YA estaba registrado. Informalo al jefe sin registrar de nuevo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACTUALIZACIÓN DE DATOS DE CLIENTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cuando el jefe da información adicional sobre un cliente existente (nombre de mascota, notas, etc.):
Delegá a Recep SIEMPRE con este formato exacto:
"Actualizar [NOMBRE APELLIDO]: campo [Nombre del campo] = [valor], campo [Nombre del campo 2] = [valor2]"

Ejemplos válidos:
• "Actualizar Daniela Spinelli: campo Nombre del perro = Aron, campo Raza del perro = Border Collie"
• "Actualizar Fernando Barrios: campo Nombre del perro = Canela"

❌ NO uses lenguaje ambiguo como "anotá que..." — el Recep necesita el formato campo = valor.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BRIEFING DE CLIENTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cuando el jefe mencione el nombre de un cliente — "hoy viene Daniela", "qué tiene pendiente María" — PRIMERO usá `briefing_cliente`.
Formato del resumen:
"📋 [Nombre] — Tel: XXXX | Alta: DD/MM/AAAA
Notas: [comentarios]
🛍️ Productos disponibles: [lista con precios]
💡 Sugerencia: [producto relevante según notas del cliente]"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO DE RESPUESTA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Una oración de qué hiciste / qué delegaste
- El resultado concreto (qué quedó registrado, qué se redactó, etc.)
- Si falta información: pedila directamente, sin rodeos."""

# Historial por (tenant_id, user_email) — cada usuario tiene su propia sesión
_HISTORY: dict[tuple[str, str], list[dict]] = {}
MAX_HISTORY = 40

# Referencias fuertes a tasks de background para evitar GC prematuro.
# Python solo guarda weak refs a tasks; sin esto pueden ser eliminadas antes de terminar.
_bg_tasks: set = set()


def _fire_and_track(coro) -> None:
    """Crea un task con referencia fuerte. Se auto-descarta al completar."""
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


_CONFIRMACIONES = {"sí", "si", "dale", "ok", "confirmá", "confirma", "confirmo",
                   "sigue", "adelante", "hacelo", "anotalo", "registralo", "procedé",
                   "procede", "continúa", "continua", "perfecto", "listo", "vamos"}

_NEGACIONES = {"no", "cancelá", "cancela", "pará", "para", "detené", "detene", "olvídalo",
               "olvidalo", "no ejecutes", "no hagas"}


def _es_confirmacion(msg: str) -> bool:
    """Detecta si el mensaje es una confirmación de una acción pendiente."""
    m = msg.strip().lower().rstrip(".,!¡¿?")
    return m in _CONFIRMACIONES or any(w in m for w in _CONFIRMACIONES)


def _es_negacion(msg: str) -> bool:
    m = msg.strip().lower().rstrip(".,!¡¿?")
    return m in _NEGACIONES or any(w in m for w in _NEGACIONES)


def _hay_confirmacion_pendiente(history: list[dict] | None = None) -> bool:
    if history is None:
        history = []
    for msg in reversed(history):
        if msg["role"] == "assistant":
            content = msg["content"] if isinstance(msg["content"], str) else ""
            return "¿confirmás?" in content.lower() or "(sí/no)" in content.lower()
    return False


async def run_vp(user_message: str, broadcast: Broadcaster = None,
                 tenant_id: str = "", user_email: str = "") -> str:
    history_key = (tenant_id, user_email)
    history = _HISTORY.setdefault(history_key, [])

    # Setear el tenant_id y spreadsheet_id en ContextVars para que todos los
    # agentes usen la planilla correcta sin necesidad de pasar el ID explícitamente.
    if tenant_id:
        set_tenant_id_ctx(tenant_id)
        try:
            from db.admin_models import get_tenant
            tenant_data = await get_tenant(tenant_id)
            # Usar `or ""` en lugar de default="" porque SQLite NULL es Python None
            sid = (tenant_data or {}).get("spreadsheet_id") or ""
            if sid:
                set_tenant_spreadsheet_id_ctx(sid)
                log.debug("run_vp: spreadsheet_id seteado para tenant %s", tenant_id)
            else:
                log.warning("run_vp: tenant %s no tiene spreadsheet_id en DB", tenant_id)
        except Exception as _e:
            log.warning("run_vp: no pudo cargar spreadsheet_id del tenant %s: %s", tenant_id, _e)

    # Enriquecer el mensaje si es una confirmación para que el VP tenga contexto claro
    mensaje_enriquecido = user_message
    if _es_confirmacion(user_message) and _hay_confirmacion_pendiente(history):
        mensaje_enriquecido = (
            f"{user_message}\n\n"
            "[SISTEMA: El jefe acaba de confirmar la acción que vos describiste en el turno anterior. "
            "Ejecutá esa acción ahora sin volver a pedir confirmación.]"
        )
    elif _es_negacion(user_message) and _hay_confirmacion_pendiente(history):
        mensaje_enriquecido = (
            f"{user_message}\n\n"
            "[SISTEMA: El jefe canceló la acción. Informalo y no ejecutes nada.]"
        )

    if broadcast:
        await broadcast({
            "type": "agent_state", "agent": "vp",
            "state": "thinking", "message": "Analizando la instrucción...",
        })

    # Construir system prompt dinámico con memoria + config del negocio
    try:
        memoria  = await obtener_memoria(limit=25, tenant_id=tenant_id)
        config   = await get_all_config(tenant_id=tenant_id)
        contexto = construir_contexto_memoria(memoria, config, user_email=user_email)
        system   = f"{contexto}\n\n{_VP_SYSTEM}" if contexto else _VP_SYSTEM
    except Exception:
        system = _VP_SYSTEM

    history.append({"role": "user", "content": mensaje_enriquecido})
    messages = list(history)
    iterations = 0

    try:
        while True:
            if iterations >= MAX_TOOL_ITERATIONS:
                result = "Tarea demasiado compleja para procesar en un solo paso. Intentá dividirla en instrucciones más simples."
                log.warning("VP: límite de iteraciones (%d) alcanzado", MAX_TOOL_ITERATIONS)
                break

            response = await call_with_retry(
                _client.messages.create,
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=system,
                tools=_TOOLS,
                messages=messages,
            )
            iterations += 1

            if response.stop_reason == "end_turn":
                result = safe_text(response.content)
                history.append({"role": "assistant", "content": result})
                if len(history) > MAX_HISTORY:
                    _HISTORY[history_key] = history[-MAX_HISTORY:]
                break

            # Procesar tool_use
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                agent_id = block.name.replace("delegar_", "")
                task     = block.input.get("tarea", "") or block.input.get("problema", "")
                agent    = _AGENTS.get(agent_id)

                if broadcast:
                    await broadcast({
                        "type": "agent_message", "from": "vp",
                        "to": agent_id, "message": truncate(task, 100),
                    })

                # ── Tools directas del VP ────────────────────────────────────
                if block.name == "agregar_columna_personalizada":
                    hoja           = block.input.get("hoja", "")
                    nombre_columna = block.input.get("nombre_columna", "")
                    if broadcast:
                        await broadcast({
                            "type": "agent_state", "agent": "vp",
                            "state": "working",
                            "message": f"Agregando columna '{nombre_columna}' en {hoja}...",
                        })
                    try:
                        agent_result = sh.agregar_columna_personalizada(hoja, nombre_columna)
                    except Exception as e:
                        agent_result = f"Error al agregar columna: {e}"
                        log.error("agregar_columna_personalizada: %s", e, exc_info=True)

                elif block.name == "briefing_cliente":
                    nombre = block.input.get("nombre", "")
                    if broadcast:
                        await broadcast({
                            "type": "agent_state", "agent": "vp",
                            "state": "working", "message": f"Consultando ficha de {nombre}...",
                        })
                    try:
                        import json as _json
                        briefing = sh.briefing_cliente(nombre)
                        agent_result = _json.dumps(briefing, ensure_ascii=False)
                    except Exception as e:
                        agent_result = f"Error al consultar briefing de '{nombre}': {e}"
                        log.error("briefing_cliente(%s): %s", nombre, e, exc_info=True)

                elif agent:
                    try:
                        agent_result = await agent.run(task, broadcast)
                    except Exception as e:
                        agent_result = f"Error inesperado en {agent_id}: {e}"
                        log.error("VP → %s falló: %s", agent_id, e, exc_info=True)
                else:
                    agent_result = f"Agente '{agent_id}' no encontrado."

                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     str(agent_result),
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user",      "content": tool_results})

    except Exception as e:
        log.error("VP falló completamente: %s", e, exc_info=True)
        result = f"Ocurrió un error al procesar tu instrucción. El equipo técnico fue notificado. Detalle: {e}"

    if broadcast:
        await broadcast({"type": "vp_response", "message": result})
        await broadcast({"type": "agent_state", "agent": "vp", "state": "idle", "message": ""})

    # Extraer aprendizajes en background con referencia fuerte para evitar GC prematuro
    _fire_and_track(procesar_post_conversacion(
        user_message, result, tenant_id=tenant_id, user_email=user_email
    ))

    return result
