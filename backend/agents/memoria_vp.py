"""
Memoria privada del VP.

Después de cada conversación, extrae aprendizajes sobre las preferencias del jefe
y los almacena de forma privada. Estos aprendizajes se inyectan en el contexto del
VP en conversaciones futuras para que sea más autosuficiente y no repita preguntas.

EL USUARIO NUNCA VE ESTE CONTENIDO — es uso interno exclusivo del VP.
"""
import json
import logging
import os

from anthropic import Anthropic
from db.models import guardar_aprendizaje, obtener_memoria
from .utils import call_with_retry

log = logging.getLogger("pokeoffice.memoria")

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_EXTRACTION_PROMPT = """Analizás el intercambio entre el jefe y el equipo.
Tu tarea: extraer aprendizajes CONCRETOS y ACCIONABLES sobre cómo le gusta trabajar al jefe.

Tipos de aprendizajes:
- preferencia: cómo quiere que se hagan las cosas ("prefiere respuestas cortas")
- patron: algo recurrente ("los lunes pide el balance")
- excepcion: cuándo NO pedir confirmación ("si dice 'anotalo directo' ejecutar sin preguntar")
- cliente: info relevante sobre un cliente frecuente
- estilo: tono, formalidad, forma de comunicarse

Reglas ESTRICTAS:
1. Solo extraé si es genuinamente útil para conversaciones FUTURAS
2. Máximo 2 aprendizajes por conversación
3. Si no hay nada nuevo y útil: devolvé []
4. Cada aprendizaje: máximo 25 palabras, específico, accionable
5. NO repitas aprendizajes obvios o genéricos

Formato de respuesta (JSON puro, sin markdown):
[{"tipo": "preferencia|patron|excepcion|cliente|estilo", "aprendizaje": "...", "relevancia": 1-10}]
"""


async def extraer_aprendizajes(user_message: str, vp_response: str,
                                memoria_actual: list[dict],
                                user_email: str = "") -> list[dict]:
    """
    Analiza una conversación y extrae nuevos aprendizajes.
    Corre en background — no bloquea la respuesta al usuario.
    """
    ya_sabe = "\n".join(f"- {m['aprendizaje']}" for m in memoria_actual[:20])
    usuario_str = f"\nUSUARIO QUE HABLÓ: {user_email}" if user_email else ""

    prompt = (
        f"INTERCAMBIO:{usuario_str}\n"
        f"Jefe: {user_message}\n"
        f"VP respondió: {vp_response[:300]}\n\n"
        f"APRENDIZAJES QUE YA TENÉS (no repetir):\n{ya_sabe or 'Ninguno aún.'}"
    )

    try:
        resp = await call_with_retry(
            _client.messages.create,
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=_EXTRACTION_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        aprendizajes = json.loads(raw)
        if not isinstance(aprendizajes, list):
            return []
        return aprendizajes
    except Exception as e:
        log.error("extraer_aprendizajes: %s", e)
        return []


async def procesar_post_conversacion(user_message: str, vp_response: str,
                                      tenant_id: str = "", user_email: str = ""):
    """
    Punto de entrada: extrae y guarda aprendizajes tras cada conversación.
    Si el VP reportó dificultad técnica, dispara análisis del Master DEV.
    Se llama en background — no bloquea nada.
    """
    import asyncio

    # Extraer aprendizajes del VP
    try:
        memoria_actual = await obtener_memoria(limit=30, tenant_id=tenant_id)
        nuevos = await extraer_aprendizajes(user_message, vp_response, memoria_actual,
                                            user_email=user_email)
        for item in nuevos:
            if isinstance(item, dict) and item.get("aprendizaje"):
                await guardar_aprendizaje(
                    tipo=item.get("tipo", "preferencia"),
                    aprendizaje=item["aprendizaje"],
                    contexto=user_message[:100],
                    relevancia=min(10, max(1, int(item.get("relevancia", 5)))),
                    tenant_id=tenant_id,
                    user_email=user_email,
                )
                log.info("Nuevo aprendizaje [%s] (%s): %s",
                         item.get("tipo"), user_email or "anon", item["aprendizaje"])
    except Exception as e:
        log.error("procesar_post_conversacion (memoria): %s", e)

    # Si el VP tuvo una dificultad técnica → Master DEV analiza en background
    if "dificultad técnica" in vp_response.lower():
        try:
            from .master_dev import analizar_conversacion
            asyncio.create_task(analizar_conversacion(user_message, vp_response, tenant_id=tenant_id))
            log.info("master_dev: análisis disparado para tenant=%s", tenant_id)
        except Exception as e:
            log.error("procesar_post_conversacion (master_dev): %s", e)


def construir_contexto_memoria(memoria: list[dict], config: dict,
                               user_email: str = "") -> str:
    """
    Construye el bloque de contexto privado que se inyecta al inicio
    del system prompt del VP en cada conversación.
    """
    partes = []

    # Info del negocio
    nombre_negocio = config.get("nombre_negocio", "")
    nombre_jefe    = config.get("nombre_jefe", "")
    tipo_negocio   = config.get("tipo_negocio", "")
    moneda         = config.get("moneda", "ARS")

    if nombre_negocio or nombre_jefe:
        partes.append("CONTEXTO DEL NEGOCIO:")
        if nombre_negocio: partes.append(f"  Negocio: {nombre_negocio}")
        if tipo_negocio:   partes.append(f"  Tipo: {tipo_negocio}")
        if nombre_jefe:    partes.append(f"  Jefe principal: {nombre_jefe}")
        partes.append(f"  Moneda: {moneda}")

    # Usuario activo en esta sesión
    if user_email:
        partes.append(f"\nUSUARIO ACTIVO AHORA: {user_email}")
        partes.append(
            "  → Dirigite a esta persona directamente. "
            "Si conocés su nombre por la memoria, usalo."
        )

    # Memoria del VP — separada por usuario cuando aplica
    if memoria:
        etiquetas = {
            "preferencia": "Preferencias",
            "patron":      "Patrones recurrentes",
            "excepcion":   "Cuando NO preguntar",
            "cliente":     "Clientes clave",
            "estilo":      "Estilo de comunicación",
        }

        # Aprendizajes del usuario actual (más relevantes)
        mem_usuario = [m for m in memoria if m.get("user_email") == user_email and user_email]
        mem_equipo  = [m for m in memoria if m.get("user_email") != user_email or not user_email]

        if mem_usuario:
            partes.append(f"\nLO QUE SABÉS DE ESTE USUARIO ({user_email}):")
            por_tipo: dict[str, list] = {}
            for m in mem_usuario:
                por_tipo.setdefault(m.get("tipo", "preferencia"), []).append(m["aprendizaje"])
            for tipo, items in por_tipo.items():
                partes.append(f"  {etiquetas.get(tipo, tipo.title())}:")
                for item in items[:4]:
                    partes.append(f"    • {item}")

        if mem_equipo:
            partes.append("\nDEL EQUIPO EN GENERAL:")
            por_tipo2: dict[str, list] = {}
            for m in mem_equipo:
                por_tipo2.setdefault(m.get("tipo", "preferencia"), []).append(
                    f"{m['aprendizaje']}"
                    + (f" [{m['user_email']}]" if m.get("user_email") else "")
                )
            for tipo, items in por_tipo2.items():
                partes.append(f"  {etiquetas.get(tipo, tipo.title())}:")
                for item in items[:3]:
                    partes.append(f"    • {item}")

        partes.append(
            "\nAPLICÁ ESTE CONOCIMIENTO: antes de hacer una pregunta, "
            "revisá si ya sabés la respuesta por la memoria."
        )

    return "\n".join(partes) if partes else ""
