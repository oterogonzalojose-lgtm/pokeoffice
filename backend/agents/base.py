import os
from typing import Callable, Awaitable, Optional
from anthropic import Anthropic

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

Broadcaster = Optional[Callable[[dict], Awaitable[None]]]


class BaseAgent:
    """Base class for all Pokeoffice agents."""

    agent_id: str = ""
    display_name: str = ""
    model: str = "claude-sonnet-4-6"

    def system_prompt(self) -> str:
        raise NotImplementedError

    async def run(self, task: str, broadcast: Broadcaster = None) -> str:
        await self._emit(broadcast, "thinking", f"Procesando tarea...")

        response = _client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt(),
            messages=[{"role": "user", "content": task}],
        )
        result = response.content[0].text

        await self._emit(broadcast, "done", result[:120] + ("..." if len(result) > 120 else ""))
        return result

    async def _emit(self, broadcast: Broadcaster, state: str, message: str):
        if broadcast:
            await broadcast({
                "type": "agent_state",
                "agent": self.agent_id,
                "state": state,
                "message": message,
            })
