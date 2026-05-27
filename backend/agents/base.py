import os
from typing import Callable, Awaitable, Optional
from anthropic import Anthropic

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

Broadcaster = Optional[Callable[[dict], Awaitable[None]]]


class BaseAgent:
    """
    Base para todos los agentes de Pokeoffice.

    Subclases implementan:
      - system_prompt() → str
      - tools()         → list[dict]   (schemas de herramientas, vacío por defecto)
      - execute_tool()  → str          (ejecuta la herramienta y devuelve resultado)
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

    async def run(self, task: str, broadcast: Broadcaster = None) -> str:
        agent_tools = self.tools()

        if not agent_tools:
            return await self._simple_run(task, broadcast)

        return await self._tool_run(task, broadcast, agent_tools)

    # ── Simple run (sin tools) ────────────────────────────────────────────────

    async def _simple_run(self, task: str, broadcast: Broadcaster) -> str:
        await self._emit(broadcast, "thinking", "Procesando...")

        response = _client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt(),
            messages=[{"role": "user", "content": task}],
        )
        result = response.content[0].text
        await self._emit(broadcast, "done", result[:100])
        return result

    # ── Tool run (con herramientas) ───────────────────────────────────────────

    async def _tool_run(self, task: str, broadcast: Broadcaster, agent_tools: list) -> str:
        await self._emit(broadcast, "thinking", "Analizando tarea...")

        messages = [{"role": "user", "content": task}]

        while True:
            response = _client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.system_prompt(),
                tools=agent_tools,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                result = next((b.text for b in response.content if hasattr(b, "text")), "")
                await self._emit(broadcast, "done", result[:100])
                return result

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                await self._emit(broadcast, "working", f"{block.name.replace('_', ' ').title()}...")

                try:
                    output = self.execute_tool(block.name, block.input)
                except Exception as e:
                    output = f"Error en {block.name}: {e}"

                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     output,
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user",      "content": tool_results})

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _emit(self, broadcast: Broadcaster, state: str, message: str):
        if broadcast:
            await broadcast({
                "type":    "agent_state",
                "agent":   self.agent_id,
                "state":   state,
                "message": message,
            })
