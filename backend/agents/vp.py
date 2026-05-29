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
        "description": "Delega una tarea al Gestor de Proveedores. Usá para: pedidos de compra, seguimiento de entregas, comparación de cotizaciones.",
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
CONFIRMACIÓN OBLIGATORIA ANTES DE EJECUTAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Las siguientes acciones son IRREVERSIBLES y SIEMPRE requieren confirmación previa:

🔴 ACCIONES QUE REQUIEREN CONFIRMACIÓN:
  • Registrar cualquier pago, gasto o egreso de dinero
  • Registrar ingresos o ventas
  • Enviar un mensaje/comunicación a un cliente (afecta relación comercial)
  • Emitir una orden de compra a un proveedor
  • Actualizar saldo de cuentas bancarias
  • Eliminar o modificar datos de clientes

✅ ACCIONES QUE NO REQUIEREN CONFIRMACIÓN (ejecutar directamente):
  • Consultas y búsquedas (balance, lista de clientes, stock)
  • Redacción de borradores o contenido de marketing (no se envía)
  • Briefing de clientes
  • Diagnósticos técnicos

FLUJO DE CONFIRMACIÓN:
1. Si la instrucción requiere confirmación:
   → NO ejecutes. Resumí exactamente qué vas a hacer y terminá con: "¿Confirmás? (sí/no)"
   → Ejemplo: "Voy a registrar un egreso de $5.000 — materiales de limpieza en Libro Contable y Cashflow. ¿Confirmás? (sí/no)"

2. Si el mensaje ACTUAL del jefe es una confirmación ("sí", "dale", "ok", "confirmá", "adelante", "hacelo"):
   → Revisá el turno anterior de la conversación e identificá la acción pendiente
   → Ejecutala ahora sin volver a pedir confirmación
   → Informá el resultado

3. Si el mensaje ACTUAL del jefe es una negación ("no", "cancelá", "pará"):
   → No ejecutes. Avisá que la acción fue cancelada.

IMPORTANTE: Una vez que el jefe confirmó, no vuelvas a preguntar. Ejecutá y reportá.

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

# Historial de conversación (máx 20 intercambios = 40 mensajes)
_HISTORY: list[dict] = []
MAX_HISTORY = 40


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


def _hay_confirmacion_pendiente() -> bool:
    """
    Revisa si el último turno del VP terminó pidiendo confirmación.
    Se llama ANTES de appendear el mensaje del usuario, así que _HISTORY
    ya tiene el último assistant message al final — no necesita [:-1].
    """
    for msg in reversed(_HISTORY):
        if msg["role"] == "assistant":
            content = msg["content"] if isinstance(msg["content"], str) else ""
            return "¿confirmás?" in content.lower() or "(sí/no)" in content.lower()
    return False


async def run_vp(user_message: str, broadcast: Broadcaster = None) -> str:
    global _HISTORY

    # Enriquecer el mensaje si es una confirmación para que el VP tenga contexto claro
    mensaje_enriquecido = user_message
    if _es_confirmacion(user_message) and _hay_confirmacion_pendiente():
        mensaje_enriquecido = (
            f"{user_message}\n\n"
            "[SISTEMA: El jefe acaba de confirmar la acción que vos describiste en el turno anterior. "
            "Ejecutá esa acción ahora sin volver a pedir confirmación.]"
        )
    elif _es_negacion(user_message) and _hay_confirmacion_pendiente():
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
        memoria  = await obtener_memoria(limit=25)
        config   = await get_all_config()
        contexto = construir_contexto_memoria(memoria, config)
        system   = f"{contexto}\n\n{_VP_SYSTEM}" if contexto else _VP_SYSTEM
    except Exception:
        system = _VP_SYSTEM

    _HISTORY.append({"role": "user", "content": mensaje_enriquecido})
    messages = list(_HISTORY)
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
                _HISTORY.append({"role": "assistant", "content": result})
                if len(_HISTORY) > MAX_HISTORY:
                    _HISTORY[:] = _HISTORY[-MAX_HISTORY:]
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

                # ── Tool directa del VP: briefing_cliente ─────────────────────
                if block.name == "briefing_cliente":
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

    # Extraer aprendizajes en background (no bloquea la respuesta)
    asyncio.create_task(procesar_post_conversacion(user_message, result))

    return result
