"""
Tests de consistencia de datos en Sheets.
Mockea las llamadas reales a Google Sheets y verifica que los datos escritos
sean exactamente los que se extrajeron de la instrucción natural.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, call


# ═══════════════════════════════════════════════════════════════════════════════
# CONSISTENCIA: Registro de clientes
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsistenciaCliente:

    @pytest.mark.asyncio
    async def test_datos_escritos_coinciden_con_instruccion(self):
        """
        Dado: instrucción 'Agregar cliente Juan Pérez, tel 2991234567'
        Esperado: Sheets.agregar_cliente(nombre='Juan', apellido='Pérez', telefono='2991234567')
        """
        from agents.atencion_cliente import AtencionClienteAgent
        agent = AtencionClienteAgent()

        with patch("agents.atencion_cliente.sh.agregar_cliente") as mock_agregar, \
             patch("agents.atencion_cliente.sh.buscar_cliente", return_value=[]), \
             patch("agents.atencion_cliente._client.messages.create") as mock_claude:

            mock_agregar.return_value = "Cliente #1 'Juan Pérez' agregado."
            mock_claude.return_value = MagicMock(
                content=[MagicMock(text="Cliente registrado correctamente.")]
            )

            await agent.run("Agregar cliente Juan Pérez, teléfono 2991234567")

            assert mock_agregar.called, "agregar_cliente nunca fue llamado"
            kwargs = mock_agregar.call_args.kwargs if mock_agregar.call_args.kwargs else {}
            args   = mock_agregar.call_args.args   if mock_agregar.call_args.args   else ()

            # Construir dict con lo que se pasó
            datos_escritos = {**dict(zip(["nombre","apellido","telefono","email","comentarios"], args)), **kwargs}

            assert datos_escritos.get("nombre", "") == "Juan", \
                f"INCONSISTENCIA: instrucción='Juan', Sheets recibió nombre='{datos_escritos.get('nombre')}'"
            assert datos_escritos.get("apellido", "") == "Pérez", \
                f"INCONSISTENCIA: instrucción='Pérez', Sheets recibió apellido='{datos_escritos.get('apellido')}'"
            assert "2991234567" in datos_escritos.get("telefono", "").replace(" ",""), \
                f"INCONSISTENCIA: instrucción='2991234567', Sheets recibió tel='{datos_escritos.get('telefono')}'"

    @pytest.mark.asyncio
    async def test_email_escrito_correctamente(self):
        from agents.atencion_cliente import AtencionClienteAgent
        agent = AtencionClienteAgent()

        with patch("agents.atencion_cliente.sh.agregar_cliente") as mock_agregar, \
             patch("agents.atencion_cliente.sh.buscar_cliente", return_value=[]), \
             patch("agents.atencion_cliente._client.messages.create") as mock_claude:

            mock_agregar.return_value = "OK"
            mock_claude.return_value = MagicMock(content=[MagicMock(text="Listo.")])

            await agent.run("Alta cliente María García, email maria@negocio.com")

            assert mock_agregar.called
            kwargs = mock_agregar.call_args.kwargs if mock_agregar.call_args.kwargs else {}
            args   = mock_agregar.call_args.args   if mock_agregar.call_args.args   else ()
            datos  = {**dict(zip(["nombre","apellido","telefono","email","comentarios"], args)), **kwargs}

            assert datos.get("email", "") == "maria@negocio.com", \
                f"INCONSISTENCIA email: '{datos.get('email')}' vs 'maria@negocio.com'"

    @pytest.mark.asyncio
    async def test_no_registra_duplicado(self):
        """Si el cliente ya existe, NO debe llamar a agregar_cliente."""
        from agents.atencion_cliente import AtencionClienteAgent
        agent = AtencionClienteAgent()

        cliente_existente = [{"id": "1", "nombre": "Juan", "apellido": "Pérez",
                               "telefono": "2991234567", "email": "", "comentarios": ""}]

        with patch("agents.atencion_cliente.sh.buscar_cliente", return_value=cliente_existente), \
             patch("agents.atencion_cliente.sh.agregar_cliente") as mock_agregar, \
             patch("agents.atencion_cliente._client.messages.create") as mock_claude:

            mock_claude.return_value = MagicMock(content=[MagicMock(text="El cliente ya existe.")])

            await agent.run("Agregar cliente Juan Pérez, tel 2991234567")

            assert not mock_agregar.called, \
                "BUG: agregar_cliente fue llamado aunque el cliente ya existe (duplicado potencial)"


# ═══════════════════════════════════════════════════════════════════════════════
# CONSISTENCIA: Movimientos contables
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsistenciaContador:

    @pytest.mark.asyncio
    async def test_monto_ingreso_correcto(self):
        """
        Dado: 'cobré $5000 por consulta'
        Esperado: registrar_movimiento(haber=5000.0, categoria='Ingreso')
        """
        from agents.contador import ContadorAgent
        agent = ContadorAgent()

        with patch("agents.contador.sh.registrar_movimiento") as mock_reg, \
             patch("agents.contador.sh.registrar_movimiento_cashflow") as mock_cf, \
             patch("agents.contador._client.messages.create") as mock_claude:

            mock_reg.return_value = "Registrado"
            mock_cf.return_value  = "Registrado"
            mock_claude.return_value = MagicMock(content=[MagicMock(text="Ingreso registrado.")])

            await agent.run("cobré $5000 por consulta médica")

            assert mock_reg.called, "registrar_movimiento nunca fue llamado"
            kwargs = mock_reg.call_args.kwargs if mock_reg.call_args.kwargs else {}

            assert kwargs.get("haber") == 5000.0, \
                f"INCONSISTENCIA monto: instrucción=$5000, Sheets recibió haber={kwargs.get('haber')}"
            assert kwargs.get("categoria") == "Ingreso", \
                f"INCONSISTENCIA categoría: esperaba 'Ingreso', recibió '{kwargs.get('categoria')}'"

    @pytest.mark.asyncio
    async def test_monto_egreso_correcto(self):
        from agents.contador import ContadorAgent
        agent = ContadorAgent()

        with patch("agents.contador.sh.registrar_movimiento") as mock_reg, \
             patch("agents.contador.sh.registrar_movimiento_cashflow") as mock_cf, \
             patch("agents.contador._client.messages.create") as mock_claude:

            mock_reg.return_value = "Registrado"
            mock_cf.return_value  = "Registrado"
            mock_claude.return_value = MagicMock(content=[MagicMock(text="Gasto registrado.")])

            await agent.run("gasté $12.000 en materiales de limpieza")

            assert mock_reg.called
            kwargs = mock_reg.call_args.kwargs if mock_reg.call_args.kwargs else {}

            assert kwargs.get("debe") == 12000.0, \
                f"INCONSISTENCIA monto: instrucción=$12.000, Sheets recibió debe={kwargs.get('debe')}"
            assert kwargs.get("categoria") == "Egreso", \
                f"INCONSISTENCIA categoría: '{kwargs.get('categoria')}'"

    @pytest.mark.asyncio
    async def test_ingreso_y_cashflow_mismo_monto(self):
        """El monto debe ser idéntico en Libro Contable Y en Cashflow."""
        from agents.contador import ContadorAgent
        agent = ContadorAgent()

        with patch("agents.contador.sh.registrar_movimiento") as mock_reg, \
             patch("agents.contador.sh.registrar_movimiento_cashflow") as mock_cf, \
             patch("agents.contador._client.messages.create") as mock_claude:

            mock_reg.return_value = "OK"
            mock_cf.return_value  = "OK"
            mock_claude.return_value = MagicMock(content=[MagicMock(text="OK.")])

            await agent.run("ingreso de $8000 por ventas del día")

            monto_contable = mock_reg.call_args.kwargs.get("haber")
            monto_cashflow = mock_cf.call_args.kwargs.get("ingreso") if mock_cf.called else None

            assert monto_contable == monto_cashflow, \
                f"INCONSISTENCIA entre hojas: Libro Contable={monto_contable} vs Cashflow={monto_cashflow}"

    @pytest.mark.asyncio
    async def test_descripcion_no_vacia_en_sheets(self):
        """La descripción que llega a Sheets nunca debe estar vacía."""
        from agents.contador import ContadorAgent
        agent = ContadorAgent()

        with patch("agents.contador.sh.registrar_movimiento") as mock_reg, \
             patch("agents.contador.sh.registrar_movimiento_cashflow", return_value="OK"), \
             patch("agents.contador._client.messages.create") as mock_claude:

            mock_reg.return_value = "OK"
            mock_claude.return_value = MagicMock(content=[MagicMock(text="OK.")])

            await agent.run("cobré $3500")

            kwargs = mock_reg.call_args.kwargs if mock_reg.call_args.kwargs else {}
            desc = kwargs.get("descripcion", "")

            assert desc.strip() != "", \
                f"INCONSISTENCIA: descripción vacía llegó a Sheets. " \
                f"Instrucción 'cobré $3500' no tiene contexto → debería usar fallback."


# ═══════════════════════════════════════════════════════════════════════════════
# CONSISTENCIA: Detección de intent (keyword routing)
# ═══════════════════════════════════════════════════════════════════════════════

class TestKeywordRouting:
    """
    Verifica que las instrucciones se enrutan a la acción correcta.
    Sin estas pruebas, un typo en las keywords rompe la funcionalidad silenciosamente.
    """

    @pytest.mark.asyncio
    async def test_cobro_va_a_ingreso(self):
        from agents.contador import ContadorAgent
        agent = ContadorAgent()

        with patch("agents.contador.sh.registrar_movimiento") as mock_reg, \
             patch("agents.contador.sh.registrar_movimiento_cashflow", return_value="OK"), \
             patch("agents.contador._client.messages.create") as mock_claude:

            mock_reg.return_value = "OK"
            mock_claude.return_value = MagicMock(content=[MagicMock(text="OK.")])

            await agent.run("cobré $2000 hoy")

            kwargs = mock_reg.call_args.kwargs if mock_reg.called and mock_reg.call_args else {}
            assert "haber" in kwargs, \
                f"BUG ROUTING: 'cobré' debe ir a Ingreso (haber), pero fue a: {list(kwargs.keys())}"

    @pytest.mark.asyncio
    async def test_gasto_va_a_egreso(self):
        from agents.contador import ContadorAgent
        agent = ContadorAgent()

        with patch("agents.contador.sh.registrar_movimiento") as mock_reg, \
             patch("agents.contador.sh.registrar_movimiento_cashflow", return_value="OK"), \
             patch("agents.contador._client.messages.create") as mock_claude:

            mock_reg.return_value = "OK"
            mock_claude.return_value = MagicMock(content=[MagicMock(text="OK.")])

            await agent.run("gasté $500 en papelería")

            kwargs = mock_reg.call_args.kwargs if mock_reg.called and mock_reg.call_args else {}
            assert "debe" in kwargs, \
                f"BUG ROUTING: 'gasté' debe ir a Egreso (debe), pero fue a: {list(kwargs.keys())}"

    @pytest.mark.asyncio
    async def test_agregar_va_a_registro_cliente(self):
        from agents.atencion_cliente import AtencionClienteAgent
        agent = AtencionClienteAgent()

        with patch("agents.atencion_cliente.sh.agregar_cliente") as mock_agregar, \
             patch("agents.atencion_cliente.sh.buscar_cliente", return_value=[]), \
             patch("agents.atencion_cliente._client.messages.create") as mock_claude:

            mock_agregar.return_value = "OK"
            mock_claude.return_value = MagicMock(content=[MagicMock(text="OK.")])

            await agent.run("Agregar cliente Sofía Torres, tel 2990001111")

            assert mock_agregar.called, \
                "BUG ROUTING: 'Agregar cliente' no activó agregar_cliente()"

    @pytest.mark.asyncio
    async def test_buscar_no_llama_agregar(self):
        from agents.atencion_cliente import AtencionClienteAgent
        agent = AtencionClienteAgent()

        with patch("agents.atencion_cliente.sh.buscar_cliente", return_value=[]) as mock_buscar, \
             patch("agents.atencion_cliente.sh.agregar_cliente") as mock_agregar, \
             patch("agents.atencion_cliente._client.messages.create") as mock_claude:

            mock_claude.return_value = MagicMock(content=[MagicMock(text="No encontrado.")])

            await agent.run("buscá al cliente García")

            assert mock_buscar.called, "BUG: buscar_cliente nunca fue llamado"
            assert not mock_agregar.called, \
                "BUG CRÍTICO: una búsqueda disparó agregar_cliente (podría crear registros fantasma)"
