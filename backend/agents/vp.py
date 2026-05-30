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
ANTI-DUPLICADOS — CRÍTICO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Una vez que un agente devuelve un mensaje con "✓" o "Registrado" o "registrado correctamente":
❌ NO vuelvas a delegar esa misma acción.
❌ NO llames al mismo agente dos veces para el mismo monto y concepto en el mismo turno.
✅ La tarea está completa. Continuá con la siguiente si hay más pendientes, o respondé al jefe.

Si el Contador dice "⚠ Movimiento duplicado detectado", eso significa que YA estaba registrado. Informalo al jefe sin registrar de nuevo.

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
    asyncio.create_task(procesar_post_conversacion(
        user_message, result, tenant_id=tenant_id, user_email=user_email
    ))

    return result
