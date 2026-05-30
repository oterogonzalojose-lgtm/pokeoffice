"""
Master DEV — agente de análisis de plataforma (invisible al cliente).

Se activa en background cuando el VP reporta una dificultad técnica.
Analiza qué falló o qué pidió el cliente, categoriza el evento como
'fix' o 'mejora' y lo guarda en platform_events para el equipo Pokeoffice.

El cliente nunca ve este agente ni sus conclusiones.
"""
import json
import logging
import os

from anthropic import Anthropic

log = logging.getLogger("pokeoffice.master_dev")

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_SYSTEM = """Sos el Master DEV de Pokeoffice, una plataforma SaaS multi-tenant plug & play para pequeños negocios.

CONTEXTO IMPORTANTE:
- Todos los tenants corren exactamente el mismo código. No existe personalización por tenant.
- Cualquier cambio que se haga beneficia (o afecta) a TODOS los clientes por igual.
- Los agentes de la plataforma son: VP (orquestador), Recepcionista, Contador, Proveedores, Marketing, Programador.
- Los agentes se conectan a Google Sheets del cliente para operaciones reales.

TU ROL:
Analizás conversaciones donde ocurrió una falla técnica o donde el cliente hizo un pedido que la plataforma no pudo cumplir.
Determinás si es un error de la plataforma (fix) o una mejora potencial del producto (mejora).

DEFINICIONES:
- FIX: algo que debería funcionar y no funciona (error, bug, integración rota, configuración faltante)
- MEJORA: funcionalidad nueva que el cliente pidió y que podría ser útil para la mayoría de los tenants

APLICABILIDAD (1-10):
- 10: todos los tenants lo necesitan (ej: bug que impide usar el sistema)
- 7-9: la mayoría de los tenants se beneficiarían
- 4-6: aproximadamente la mitad
- 1-3: caso muy específico, pocas chances de ser relevante para otros

Respondé SIEMPRE con JSON puro, sin markdown ni texto adicional:
{
  "tipo": "fix" | "mejora",
  "titulo": "Título descriptivo, máximo 70 caracteres",
  "descripcion": "Qué falló técnicamente o qué funcionalidad se necesita. 1-2 oraciones.",
  "razonamiento": "Por qué es fix vs mejora y por qué la aplicabilidad elegida. 1-2 oraciones.",
  "aplicabilidad": 1-10
}"""


async def analizar_conversacion(user_message: str, vp_response: str, tenant_id: str = ""):
    """
    Analiza una conversación con error técnico y guarda el resultado en platform_events.
    Se llama en background — nunca bloquea la respuesta al usuario.
    """
    try:
        prompt = (
            f"PEDIDO DEL USUARIO:\n{user_message}\n\n"
            f"RESPUESTA DEL VP (contiene mención a dificultad técnica):\n{vp_response[:600]}"
        )

        resp = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = resp.content[0].text.strip()
        data = json.loads(raw)

        if not isinstance(data, dict) or "tipo" not in data:
            log.warning("master_dev: respuesta inesperada: %s", raw[:200])
            return

        from db.admin_models import guardar_platform_event
        await guardar_platform_event(
            tenant_id=tenant_id,
            tipo=data.get("tipo", "fix"),
            titulo=str(data.get("titulo", "Error sin título"))[:120],
            descripcion=str(data.get("descripcion", "")),
            razonamiento=str(data.get("razonamiento", "")),
            aplicabilidad=min(10, max(1, int(data.get("aplicabilidad", 5)))),
        )
        log.info("master_dev: [%s] %s", data.get("tipo"), data.get("titulo"))

    except Exception as e:
        log.error("master_dev: %s", e)
