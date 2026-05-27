import os
import json
from anthropic import Anthropic
from .base import Broadcaster
from .atencion_cliente import AtencionClienteAgent
from .contador import ContadorAgent
from .proveedores import ProveedoresAgent
from .rrhh import RRHHAgent
from .marketing import MarketingAgent

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_AGENTS = {
    "atencion_cliente": AtencionClienteAgent(),
    "contador": ContadorAgent(),
    "proveedores": ProveedoresAgent(),
    "rrhh": RRHHAgent(),
    "marketing": MarketingAgent(),
}

_TOOLS = [
    {
        "name": "delegar_atencion_cliente",
        "description": "Delega una tarea al agente de Atención al Cliente. Usá para: responder consultas de clientes, gestionar turnos, redactar mensajes de aviso, cierre de atención.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tarea": {"type": "string", "description": "Instrucción clara y detallada de qué debe hacer el agente"}
            },
            "required": ["tarea"],
        },
    },
    {
        "name": "delegar_contador",
        "description": "Delega una tarea al Contador. Usá para: registro de gastos/ingresos, balances, borradores de facturas, cálculos financieros.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tarea": {"type": "string", "description": "Instrucción clara y detallada de qué debe hacer el agente"}
            },
            "required": ["tarea"],
        },
    },
    {
        "name": "delegar_proveedores",
        "description": "Delega una tarea al Gestor de Proveedores. Usá para: pedidos de compra, seguimiento de entregas, comparación de cotizaciones.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tarea": {"type": "string", "description": "Instrucción clara y detallada de qué debe hacer el agente"}
            },
            "required": ["tarea"],
        },
    },
    {
        "name": "delegar_rrhh",
        "description": "Delega una tarea al área de RRHH/Legal. Usá para: contratos, liquidaciones, normativa laboral, comunicaciones con empleados.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tarea": {"type": "string", "description": "Instrucción clara y detallada de qué debe hacer el agente"}
            },
            "required": ["tarea"],
        },
    },
    {
        "name": "delegar_marketing",
        "description": "Delega una tarea al área de Marketing. Usá para: posts de redes, copys de promociones, ideas de contenido, newsletters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tarea": {"type": "string", "description": "Instrucción clara y detallada de qué debe hacer el agente"}
            },
            "required": ["tarea"],
        },
    },
]

_VP_SYSTEM = """Sos el VP (Jefe de Gabinete) de una pequeña empresa. Tu jefe (el usuario) te da instrucciones en lenguaje natural y vos las interpretás, delegás al área correcta y supervisás la ejecución.

Tus reglas:
1. Siempre entendé bien qué necesita el jefe antes de delegar.
2. Delegá exactamente al agente correcto (o a varios si hace falta).
3. Cuando delegues, dale instrucciones claras y completas al agente.
4. Después de recibir la respuesta del agente, presentala al jefe de forma clara y útil.
5. Si la instrucción no corresponde a ningún agente, respondé vos mismo.
6. Siempre respondé en español. Sé conciso y profesional."""


async def run_vp(user_message: str, broadcast: Broadcaster = None) -> str:
    """Runs the VP orchestrator with tool_use to delegate to specialized agents."""

    if broadcast:
        await broadcast({
            "type": "agent_state",
            "agent": "vp",
            "state": "thinking",
            "message": "Analizando la instrucción...",
        })

    messages = [{"role": "user", "content": user_message}]
    all_events = []

    while True:
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=_VP_SYSTEM,
            tools=_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            if broadcast:
                await broadcast({
                    "type": "vp_response",
                    "message": final_text,
                })
                await broadcast({
                    "type": "agent_state",
                    "agent": "vp",
                    "state": "idle",
                    "message": "",
                })
            return final_text

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            agent_id = block.name.replace("delegar_", "")
            task = block.input.get("tarea", "")
            agent = _AGENTS.get(agent_id)

            if broadcast:
                await broadcast({
                    "type": "agent_message",
                    "from": "vp",
                    "to": agent_id,
                    "message": task[:100],
                })

            if agent:
                result = await agent.run(task, broadcast)
            else:
                result = f"Agente '{agent_id}' no encontrado."

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
