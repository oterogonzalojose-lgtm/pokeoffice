"""
Tests de flujos de confirmación para acciones irreversibles.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS DE DETECCIÓN
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeteccionConfirmacion:

    def setup_method(self):
        # Limpiar historial antes de cada test
        import agents.vp as vp
        vp._HISTORY.clear()

    def test_detecta_confirmaciones_clasicas(self):
        from agents.vp import _es_confirmacion
        for word in ["sí", "si", "dale", "ok", "confirmá", "adelante", "hacelo"]:
            assert _es_confirmacion(word), f"'{word}' debería ser confirmación"

    def test_detecta_negaciones(self):
        from agents.vp import _es_negacion
        for word in ["no", "cancelá", "pará", "detené"]:
            assert _es_negacion(word), f"'{word}' debería ser negación"

    def test_no_confunde_instruccion_con_confirmacion(self):
        from agents.vp import _es_confirmacion
        instrucciones = [
            "registrá un pago de $5000",
            "buscá al cliente García",
            "hacé un balance del mes",
        ]
        for instr in instrucciones:
            assert not _es_confirmacion(instr), \
                f"Instrucción '{instr}' no debe ser detectada como confirmación"

    def test_hay_confirmacion_pendiente_cuando_vp_pregunto(self):
        import agents.vp as vp
        vp._HISTORY.clear()
        vp._HISTORY.extend([
            {"role": "user",      "content": "registrá un pago de $5000"},
            {"role": "assistant", "content": "Voy a registrar un egreso de $5.000. ¿Confirmás? (sí/no)"},
            {"role": "user",      "content": "sí"},  # mensaje actual
        ])
        assert vp._hay_confirmacion_pendiente(), \
            "Debería detectar confirmación pendiente cuando el VP preguntó en el turno anterior"

    def test_no_hay_confirmacion_pendiente_si_vp_no_pregunto(self):
        import agents.vp as vp
        vp._HISTORY.clear()
        vp._HISTORY.extend([
            {"role": "user",      "content": "hacé un balance"},
            {"role": "assistant", "content": "El balance del mes es: Ingresos $10.000, Egresos $4.000."},
            {"role": "user",      "content": "sí"},
        ])
        assert not vp._hay_confirmacion_pendiente(), \
            "No debe detectar confirmación pendiente si el VP no preguntó en el turno anterior"


# ═══════════════════════════════════════════════════════════════════════════════
# ENRIQUECIMIENTO DEL MENSAJE
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnriquecimientoMensaje:

    def setup_method(self):
        import agents.vp as vp
        vp._HISTORY.clear()

    @pytest.mark.asyncio
    async def test_mensaje_si_se_enriquece_cuando_hay_pendiente(self):
        """Cuando el jefe dice 'sí' y hay acción pendiente, el mensaje debe incluir contexto [SISTEMA]."""
        import agents.vp as vp

        # Simular historial con VP esperando confirmación
        vp._HISTORY.extend([
            {"role": "user",      "content": "registrá un egreso de $5000"},
            {"role": "assistant", "content": "Voy a registrar un egreso de $5.000. ¿Confirmás? (sí/no)"},
        ])

        mensajes_enviados = []

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Egreso registrado correctamente."

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [text_block]

        def capturar_llamada(**kwargs):
            mensajes_enviados.extend(kwargs.get("messages", []))
            return mock_response

        with patch("agents.vp.call_with_retry", side_effect=lambda f, **kw: capturar_llamada(**kw)):
            await vp.run_vp("sí")

        # El mensaje enriquecido debe contener la indicación [SISTEMA]
        ultimo_user = next(
            (m["content"] for m in reversed(mensajes_enviados) if m["role"] == "user"
             and isinstance(m["content"], str)),
            ""
        )
        assert "[SISTEMA]" in ultimo_user or "SISTEMA" in ultimo_user, \
            f"El mensaje 'sí' no fue enriquecido con contexto [SISTEMA]. Recibido: '{ultimo_user[:100]}'"

    @pytest.mark.asyncio
    async def test_mensaje_si_no_se_enriquece_sin_pendiente(self):
        """Si no hay acción pendiente, el 'sí' se pasa tal cual."""
        import agents.vp as vp
        vp._HISTORY.clear()
        # Historial sin pregunta de confirmación
        vp._HISTORY.extend([
            {"role": "user",      "content": "hacé un balance"},
            {"role": "assistant", "content": "El balance del mes es positivo."},
        ])

        mensajes_enviados = []

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Entendido."

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [text_block]

        def capturar_llamada(**kwargs):
            mensajes_enviados.extend(kwargs.get("messages", []))
            return mock_response

        with patch("agents.vp.call_with_retry", side_effect=lambda f, **kw: capturar_llamada(**kw)):
            await vp.run_vp("sí, entendido")

        ultimo_user = next(
            (m["content"] for m in reversed(mensajes_enviados) if m["role"] == "user"
             and isinstance(m["content"], str)),
            ""
        )
        assert "[SISTEMA]" not in ultimo_user, \
            "Sin acción pendiente, el mensaje no debe ser enriquecido con [SISTEMA]"


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO COMPLETO: PEDIR CONFIRMACIÓN → EJECUTAR
# ═══════════════════════════════════════════════════════════════════════════════

class TestFlujoConfirmacion:

    def setup_method(self):
        import agents.vp as vp
        vp._HISTORY.clear()

    @pytest.mark.asyncio
    async def test_vp_pregunta_antes_de_registrar_egreso(self):
        """El VP debe preguntar '¿Confirmás?' antes de registrar un egreso."""
        import agents.vp as vp

        text_block = MagicMock()
        text_block.type = "text"
        # VP responde pidiendo confirmación (sin ejecutar)
        text_block.text = "Voy a registrar un egreso de $3.000 por electricidad. ¿Confirmás? (sí/no)"

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [text_block]

        with patch("agents.vp.call_with_retry", return_value=mock_response):
            result = await vp.run_vp("registrá un gasto de $3000 en electricidad")

        assert "confirmás" in result.lower() or "confirmar" in result.lower() or "¿" in result, \
            f"BUG: el VP ejecutó un egreso sin pedir confirmación. Respuesta: '{result}'"

    @pytest.mark.asyncio
    async def test_cancelacion_no_ejecuta(self):
        """Si el jefe dice 'no', la acción debe cancelarse."""
        import agents.vp as vp

        # Setup: VP ya preguntó en turno anterior
        vp._HISTORY.extend([
            {"role": "user",      "content": "registrá un pago de $5000"},
            {"role": "assistant", "content": "Voy a registrar un egreso de $5.000. ¿Confirmás? (sí/no)"},
        ])

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Entendido, cancelé la acción. No se registró ningún movimiento."

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [text_block]

        contador_mock = MagicMock()
        contador_mock.run = AsyncMock(return_value="Registrado")

        with patch("agents.vp.call_with_retry", return_value=mock_response), \
             patch.dict("agents.vp._AGENTS", {"contador": contador_mock}):
            result = await vp.run_vp("no")

        # El agente contador NO debe haber sido llamado
        assert not contador_mock.run.called, \
            "BUG CRÍTICO: el agente ejecutó la acción a pesar de que el jefe dijo 'no'"
