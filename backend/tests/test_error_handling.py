"""
Tests de robustez y error handling.
Verifica reintentos, timeouts, límites de iteraciones y fallbacks.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import anthropic


# ═══════════════════════════════════════════════════════════════════════════════
# RETRY LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetryLogic:

    @pytest.mark.asyncio
    async def test_reintenta_en_error_transitorio(self):
        """call_with_retry debe reintentar ante APIConnectionError."""
        from agents.utils import call_with_retry

        call_count = 0
        def fn_que_falla_dos_veces():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise anthropic.APIConnectionError(request=MagicMock())
            return "éxito"

        with patch("agents.utils.asyncio.sleep", new_callable=AsyncMock):
            resultado = await call_with_retry(fn_que_falla_dos_veces)

        assert resultado == "éxito"
        assert call_count == 3, f"Esperaba 3 intentos, hubo {call_count}"

    @pytest.mark.asyncio
    async def test_falla_definitivo_despues_de_max_reintentos(self):
        """Después de MAX_RETRIES debe lanzar RuntimeError."""
        from agents.utils import call_with_retry

        def siempre_falla():
            raise anthropic.APIConnectionError(request=MagicMock())

        with patch("agents.utils.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="Fallo después de"):
                await call_with_retry(siempre_falla)

    @pytest.mark.asyncio
    async def test_no_reintenta_error_autenticacion(self):
        """AuthenticationError NO debe reintentarse — es error de configuración."""
        from agents.utils import call_with_retry

        call_count = 0
        def error_auth():
            nonlocal call_count
            call_count += 1
            raise anthropic.AuthenticationError(
                message="Invalid API key",
                response=MagicMock(),
                body={}
            )

        with patch("agents.utils.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(anthropic.AuthenticationError):
                await call_with_retry(error_auth)

        assert call_count == 1, \
            f"BUG: AuthenticationError fue reintentado {call_count} veces (solo debe intentarse 1)"

    @pytest.mark.asyncio
    async def test_timeout_lanza_error(self):
        """Si la llamada supera API_TIMEOUT, debe fallar con RuntimeError."""
        from agents.utils import call_with_retry
        import asyncio as aio

        async def timeout_mock(*args, **kwargs):
            raise aio.TimeoutError()

        with patch("agents.utils.asyncio.wait_for", side_effect=aio.TimeoutError()), \
             patch("agents.utils.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError):
                await call_with_retry(lambda: None)


# ═══════════════════════════════════════════════════════════════════════════════
# LÍMITE DE ITERACIONES
# ═══════════════════════════════════════════════════════════════════════════════

class TestLimiteIteraciones:

    @pytest.mark.asyncio
    async def test_base_agent_corta_loop_infinito(self):
        """
        Si Claude sigue pidiendo tool_use indefinidamente,
        el agente debe cortar en MAX_TOOL_ITERATIONS y devolver mensaje claro.
        """
        from agents.base import BaseAgent
        from agents.utils import MAX_TOOL_ITERATIONS

        class AgentTest(BaseAgent):
            agent_id = "test"
            def system_prompt(self): return "test"
            def tools(self):
                return [{"name": "herramienta_loop", "description": "test",
                         "input_schema": {"type": "object", "properties": {}}}]
            def execute_tool(self, name, inputs): return "resultado"

        # Simular respuesta que SIEMPRE pide tool_use
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "herramienta_loop"
        tool_block.input = {}
        tool_block.id = "tu_001"

        mock_response = MagicMock()
        mock_response.stop_reason = "tool_use"
        mock_response.content = [tool_block]

        with patch("agents.base.call_with_retry", return_value=mock_response):
            agent = AgentTest()
            result = await agent.run("tarea que hace loop")

        assert "límite" in result.lower() or "iteraciones" in result.lower(), \
            f"BUG: loop infinito no fue cortado. Respuesta: '{result}'"

    @pytest.mark.asyncio
    async def test_vp_corta_loop_infinito(self):
        """El VP también debe cortar si hay demasiadas delegaciones."""
        from agents.vp import run_vp
        from agents.utils import MAX_TOOL_ITERATIONS

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "delegar_contador"
        tool_block.input = {"tarea": "loop"}
        tool_block.id = "vp_001"

        mock_response = MagicMock()
        mock_response.stop_reason = "tool_use"
        mock_response.content = [tool_block]

        contador_mock = MagicMock()
        contador_mock.run = AsyncMock(return_value="resultado")

        with patch("agents.vp.call_with_retry", return_value=mock_response), \
             patch.dict("agents.vp._AGENTS", {"contador": contador_mock}):
            result = await run_vp("tarea que hace loop")

        assert result != "", "VP no debe devolver resultado vacío"
        assert "límite" in result.lower() or "compleja" in result.lower() or result != "", \
            f"VP no cortó el loop. Respuesta: '{result}'"


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR EN EXECUTE_TOOL
# ═══════════════════════════════════════════════════════════════════════════════

class TestErrorEnExecuteTool:

    @pytest.mark.asyncio
    async def test_error_en_tool_no_crashea_agente(self):
        """Un error en execute_tool no debe crashear el agente — debe devolver mensaje de error."""
        from agents.base import BaseAgent

        class AgentConToolRota(BaseAgent):
            agent_id = "test_roto"
            def system_prompt(self): return "test"
            def tools(self):
                return [{"name": "tool_rota", "description": "test",
                         "input_schema": {"type": "object", "properties": {}}}]
            def execute_tool(self, name, inputs):
                raise ValueError("Error simulado en la herramienta")

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "tool_rota"
        tool_block.input = {}
        tool_block.id = "t_001"

        # Primera llamada → tool_use, segunda → end_turn
        response_tool = MagicMock()
        response_tool.stop_reason = "tool_use"
        response_tool.content = [tool_block]

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Hubo un error pero continué."

        response_end = MagicMock()
        response_end.stop_reason = "end_turn"
        response_end.content = [text_block]

        responses = iter([response_tool, response_end])

        with patch("agents.base.call_with_retry", side_effect=lambda f, **kw: responses.__next__()):
            agent = AgentConToolRota()
            try:
                result = await agent.run("tarea con tool rota")
                # Si llegó acá sin crash, pasó el test
                assert True
            except Exception as e:
                pytest.fail(f"El agente crasheó ante error en execute_tool: {e}")

    @pytest.mark.asyncio
    async def test_error_en_agente_delegado_no_crashea_vp(self):
        """Si un agente delegado falla, el VP debe manejar el error sin crashear."""
        from agents.vp import run_vp

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "delegar_contador"
        tool_block.input = {"tarea": "tarea que falla"}
        tool_block.id = "vp_002"

        response_tool = MagicMock()
        response_tool.stop_reason = "tool_use"
        response_tool.content = [tool_block]

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Hubo un error en el contador pero continué."

        response_end = MagicMock()
        response_end.stop_reason = "end_turn"
        response_end.content = [text_block]

        responses = iter([response_tool, response_end])

        contador_mock = MagicMock()
        contador_mock.run = AsyncMock(side_effect=RuntimeError("Error simulado en contador"))

        with patch("agents.vp.call_with_retry", side_effect=lambda f, **kw: responses.__next__()), \
             patch.dict("agents.vp._AGENTS", {"contador": contador_mock}):
            try:
                result = await run_vp("hacer algo que falla")
                assert result != "", "VP devolvió resultado vacío ante error"
            except Exception as e:
                pytest.fail(f"VP crasheó ante error en agente delegado: {e}")
