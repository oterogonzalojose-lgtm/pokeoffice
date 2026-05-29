import logging
import os
from typing import Callable, Awaitable, Optional

from anthropic import Anthropic

from .utils import call_with_retry, safe_text, truncate, MAX_TOOL_ITERATIONS

log = logging.getLogger("pokeoffice")

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

Broadcaster = Optional[Callable[[dict], Awaitable[None]]]


class BaseAgent:
    """
    Base para todos los agentes de Pokeoffice.

    Subclases implementan:
      - system_prompt() → str
      - tools()         → list[dict]   (vacío por defecto)
      - execute_tool()  → str
    """

    agent_id:     str = ""
    display_name: str = ""
    model:        str = "claude-sonnet-4-6"

    def system_prompt(self) -> str:
        raise NotImplementedError

    def tools(self) -> list[dict]:
        return []

    def execute_tool(self, name: str, inputs: dict) -> str:
        raise NotImplementedError(f"Tool '{name}' no implementada en {self.__class__.__name__}")

    # ── Entry point ───────────────────────────────────────────────────────────

    async def run(self, task: str, broadcast: Broadcaster = None) -> str:
        try:
            agent_tools = self.tools()
            if not agent_tools:
                return await self._simple_run(task, broadcast)
            return await self._tool_run(task, broadcast, agent_tools)
        except Exception as e:
            msg = f"[{self.display_name or self.agent_id}] Error: {e}"
            log.error(msg, exc_info=True)
            await self._emit(broadcast, "done", "Error al procesar la tarea")
            return f"Error en agente {self.display_name or self.agent_id}: {e}"

    # ── Simple run (sin tools) ────────────────────────────────────────────────

    async def _simple_run(self, task: str, broadcast: Broadcaster) -> str:
        await self._emit(broadcast, "thinking", "Procesando...")

        response = await call_with_retry(
            _client.messages.create,
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt(),
            messages=[{"role": "user", "content": task}],
        )
        result = safe_text(response.content)
        await self._emit(broadcast, "done", truncate(result))
        return result

    # ── Tool run (con herramientas) ───────────────────────────────────────────

    async def _tool_run(self, task: str, broadcast: Broadcaster, agent_tools: list) -> str:
        await self._emit(broadcast, "thinking", "Analizando tarea...")

        messages = [{"role": "user", "content": task}]
        iterations = 0

        while True:
            if iterations >= MAX_TOOL_ITERATIONS:
                msg = f"Límite de iteraciones alcanzado ({MAX_TOOL_ITERATIONS}) — tarea demasiado compleja."
                log.warning("%s: %s", self.agent_id, msg)
                await self._emit(broadcast, "done", "Tarea interrumpida por límite de pasos")
                return msg

            response = await call_with_retry(
                _client.messages.create,
                model=self.model,
                max_tokens=2048,
                system=self.system_prompt(),
                tools=agent_tools,
                messages=messages,
            )
            iterations += 1

            if response.stop_reason == "end_turn":
                result = safe_text(response.content)
                await self._emit(broadcast, "done", truncate(result))
                return result

            # Procesar tool_use
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_label = block.name.replace("_", " ").title()
                await self._emit(broadcast, "working", f"{tool_label}...")

                try:
                    output = self.execute_tool(block.name, block.input)
                except Exception as e:
                    output = f"Error al ejecutar {block.name}: {e}"
                    log.error("%s.execute_tool(%s): %s", self.agent_id, block.name, e, exc_info=True)

                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     str(output),
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user",      "content": tool_results})

    # ── Helper ────────────────────────────────────────────────────────────────

    async def _emit(self, broadcast: Broadcaster, state: str, message: str):
        if broadcast:
            await broadcast({
                "type":    "agent_state",
                "agent":   self.agent_id,
                "state":   state,
                "message": message,
            })
