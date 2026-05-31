"""
Utilidades compartidas: retry con backoff exponencial, timeout, límites de seguridad.
"""
import asyncio
import logging
from functools import wraps

import anthropic

log = logging.getLogger("pokeoffice")

# ── Constantes de seguridad ────────────────────────────────────────────────────
MAX_TOOL_ITERATIONS = 12    # máximo de rondas de tool_use antes de cortar
MAX_RETRIES         = 3     # intentos por llamada a la API
RETRY_BASE_DELAY    = 1.5   # segundos base para backoff exponencial
API_TIMEOUT         = 60.0  # segundos máximos por llamada

# Excepciones de la API que se consideran transitorias (vale la pena reintentar)
_RETRYABLE = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.InternalServerError,
    anthropic.RateLimitError,
)


async def call_with_retry(fn, *args, **kwargs):
    """
    Llama a fn(*args, **kwargs) con reintentos y backoff exponencial.
    fn debe ser sincrónica (los clientes Anthropic no son async).
    Corre en un executor para no bloquear el event loop.
    """
    loop = asyncio.get_running_loop()
    last_exc = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Corre la llamada sincrónica en un thread para no bloquear
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: fn(*args, **kwargs)),
                timeout=API_TIMEOUT,
            )
            return result

        except asyncio.TimeoutError:
            last_exc = TimeoutError(f"La API no respondió en {API_TIMEOUT}s")
            log.warning("Timeout en intento %d/%d", attempt, MAX_RETRIES)

        except _RETRYABLE as e:
            last_exc = e
            log.warning("Error transitorio (intento %d/%d): %s", attempt, MAX_RETRIES, e)

        except anthropic.AuthenticationError:
            raise  # no reintentar errores de auth

        except Exception as e:
            last_exc = e
            log.error("Error inesperado en llamada a API: %s", e)
            break  # error no transitorio → no reintentar

        if attempt < MAX_RETRIES:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            log.info("Reintentando en %.1fs...", delay)
            await asyncio.sleep(delay)

    raise RuntimeError(f"Fallo después de {MAX_RETRIES} intentos: {last_exc}") from last_exc


def safe_text(content_blocks) -> str:
    """Extrae el primer bloque de texto de la respuesta, con fallback."""
    for b in content_blocks:
        if hasattr(b, "text") and b.text:
            return b.text
    return ""


def truncate(text: str, n: int = 120) -> str:
    return text[:n] + ("…" if len(text) > n else "")
