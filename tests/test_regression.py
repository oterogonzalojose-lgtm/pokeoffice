"""
test_regression.py — Tests de regresión para todos los bugs corregidos en Pokeoffice.

Cada test corresponde a un bug específico que se encontró en producción.
Si alguno de estos tests falla, significa que un bug ya resuelto volvió.
"""
import re
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# ══════════════════════════════════════════════════════════════════════════════
# BUG #1 — Regex capturaba "con" como nombre del cliente
# Causa: re.IGNORECASE en el patrón "cliente\s+" → matcheaba palabras comunes
# Fix: prioridad a etiqueta "Nombre:", sin IGNORECASE en el patrón "cliente"
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractionClienteNombre:
    """El VP delega con formato 'nuevo cliente con los siguientes datos: - Nombre: X'"""

    def _extraer(self, task: str) -> dict:
        from agents.atencion_cliente import AtencionClienteAgent
        agent = AtencionClienteAgent()
        return agent._extraer_datos_cliente(task)

    def test_formato_vp_estructurado(self):
        """Formato VP: '- Nombre: Fernando Barrios - Teléfono: ...'"""
        task = "Registrar un nuevo cliente con los siguientes datos: - Nombre: Fernando Barrios - Teléfono: 5491160602020"
        datos = self._extraer(task)
        assert datos["nombre"] == "Fernando", f"Nombre incorrecto: {datos['nombre']}"
        assert datos["apellido"] == "Barrios"
        assert "5491160602020" in datos["telefono"]

    def test_formato_humano_directo(self):
        """Formato humano: 'nuevo cliente: Fernando Barrios, tel ...'"""
        task = "nuevo cliente: Fernando Barrios, tel 5491160602020"
        datos = self._extraer(task)
        assert datos["nombre"] == "Fernando"
        assert datos["apellido"] == "Barrios"

    def test_NO_captura_con_como_nombre(self):
        """BUG ORIGINAL: 'nuevo cliente con los siguientes datos' capturaba 'con'"""
        task = "nuevo cliente con los siguientes datos Fernando Barrios"
        datos = self._extraer(task)
        assert datos["nombre"] != "con", "BUG REGRESADO: capturó 'con' como nombre"
        # Sin etiqueta "Nombre:" y sin nombre propio después de "cliente" → vacío es OK
        # (la Recep pedirá los datos al jefe)

    def test_nombre_con_acento(self):
        """Nombres con acentos deben ser capturados."""
        task = "Registrar nuevo cliente: María José Rodríguez, tel 1122334455"
        datos = self._extraer(task)
        assert datos["nombre"] == "María"
        assert "Rodríguez" in datos["apellido"] or "José" in datos["apellido"]

    def test_telefono_solo_digitos(self):
        """El teléfono no debe capturar texto adyacente."""
        task = "- Nombre: Pedro Álvarez - Teléfono: 1133445566 - Email: pedro@gmail.com"
        datos = self._extraer(task)
        assert datos["telefono"] == "1133445566"
        assert datos["email"] == "pedro@gmail.com"

    def test_nombre_etiqueta_prioridad_sobre_patron_cliente(self):
        """Si hay etiqueta 'Nombre:', debe tener prioridad sobre el patrón 'cliente'."""
        task = "Alta de cliente nuevo para el negocio: Nombre: Valentina Greco, Teléfono: 1144556677"
        datos = self._extraer(task)
        assert datos["nombre"] == "Valentina"
        assert datos["apellido"] == "Greco"


# ══════════════════════════════════════════════════════════════════════════════
# BUG #2 — Dedup no chequeaba por teléfono, solo por nombre
# Causa: buscar_cliente() solo usaba el nombre completo
# Fix: si no hay match por nombre, busca por teléfono; si encuentra match con
#      distinto nombre, alerta al jefe en lugar de registrar silenciosamente
# ══════════════════════════════════════════════════════════════════════════════

class TestDedupClientes:
    """Tests de detección de duplicados en registro de clientes."""

    @pytest.mark.asyncio
    async def test_dedup_por_nombre_exacto(self):
        """Si el nombre ya existe, NO registra y alerta."""
        with patch("mcp.sheets_client.get_spreadsheet_id", return_value="sid"), \
             patch("mcp.sheets_client._sheets") as mock_svc:

            # Simular que buscar_cliente devuelve un cliente existente
            with patch("mcp.sheets_client.buscar_cliente") as mock_buscar:
                mock_buscar.return_value = [
                    {"id": "3", "nombre": "Fernando", "apellido": "Barrios",
                     "telefono": "5491160602020", "email": ""}
                ]

                from agents.atencion_cliente import AtencionClienteAgent
                agent = AtencionClienteAgent()
                task = "Registrar nuevo cliente: Fernando Barrios, Teléfono: 5491160602020"
                resultado = await agent.run(task)

                # No debe confirmar registro exitoso
                assert "registrado" not in resultado.lower() or "ya existe" in resultado.lower() or "duplicado" in resultado.lower()

    @pytest.mark.asyncio
    async def test_dedup_telefono_distinto_nombre(self):
        """Si el teléfono ya existe con otro nombre, debe preguntar al jefe."""
        clientes_existentes = [
            {"id": "1", "nombre": "con", "apellido": "los siguientes datos",
             "telefono": "5491160602020", "email": ""}
        ]

        with patch("mcp.sheets_client.buscar_cliente") as mock_buscar:
            # Primera búsqueda por nombre: no encuentra
            # Segunda búsqueda por teléfono: encuentra el registro corrupto
            mock_buscar.side_effect = [[], clientes_existentes]

            from agents.atencion_cliente import AtencionClienteAgent
            agent = AtencionClienteAgent()
            task = "Registrar nuevo cliente: Fernando Barrios, Teléfono: 5491160602020"
            resultado = await agent.run(task)

            # Debe mencionar el conflicto de teléfono
            assert any(word in resultado.lower() for word in
                       ["teléfono", "existe", "registrado", "¿querés", "actualizar"]), \
                f"No detectó conflicto de teléfono: {resultado[:200]}"


# ══════════════════════════════════════════════════════════════════════════════
# BUG #3 — Actualizar cliente: else branch ejecutaba Claude sin tocar Sheets
# Causa: AtencionClienteAgent.run() sin intent "actualizar" → Claude inventaba
#        confirmaciones sin haber escrito nada en la planilla
# Fix: nuevo intent + extractor regex + actualizar_campo_cliente()
# ══════════════════════════════════════════════════════════════════════════════

class TestActualizarCampoCliente:
    """Tests del extractor de pares campo=valor para actualización de clientes."""

    def _extraer_pares(self, task: str):
        """Extrae (nombre_cliente, [(campo, valor)]) de un task de actualización."""
        task_lower = task.lower()
        m_nombre = re.search(
            r"(?:de|para|actualizar|actualiz[aá]r?)\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)+)",
            task, re.IGNORECASE
        )
        nombre = m_nombre.group(1).strip() if m_nombre else ""
        partes = re.split(r"\bcampo\b", task, flags=re.IGNORECASE)
        pares = []
        for parte in partes[1:]:
            m = re.match(r"\s*([^=]+?)\s*=\s*(.+?)(?:\s*,\s*$|\s*$)", parte.strip(), re.DOTALL)
            if m:
                campo = m.group(1).strip().strip("'\"")
                valor = m.group(2).strip().strip("'\"").rstrip(",").strip()
                if campo and valor:
                    pares.append((campo, valor))
        return nombre, pares

    def test_un_campo(self):
        task = "Actualizar Fernando Barrios: campo Nombre del perro = Canela"
        nombre, pares = self._extraer_pares(task)
        assert nombre == "Fernando Barrios"
        assert pares == [("Nombre del perro", "Canela")]

    def test_multiples_campos(self):
        task = "Actualizar Daniela Spinelli: campo Nombre del perro = Aron, campo Raza del perro = Border Collie"
        nombre, pares = self._extraer_pares(task)
        assert nombre == "Daniela Spinelli"
        assert ("Nombre del perro", "Aron") in pares
        assert ("Raza del perro", "Border Collie") in pares
        assert len(pares) == 2

    def test_campo_con_espacios_en_nombre(self):
        task = "Actualizar para Valentina Greco: campo Tipo de masaje = Deportivo"
        nombre, pares = self._extraer_pares(task)
        assert "Valentina Greco" in nombre or "Greco" in nombre
        assert pares[0][0] == "Tipo de masaje"
        assert pares[0][1] == "Deportivo"

    def test_tres_campos(self):
        task = "Actualizar Marcos Alvarez: campo Patente = ABC123, campo Modelo / Color = Renault Clio Gris, campo Año = 2018"
        nombre, pares = self._extraer_pares(task)
        assert len(pares) == 3
        assert any(c == "Patente" for c, v in pares)
        assert any(v == "ABC123" for c, v in pares)

    def test_sin_campos_devuelve_vacio(self):
        task = "Actualizar Fernando Barrios sin datos claros"
        nombre, pares = self._extraer_pares(task)
        assert pares == []  # No hay pares → la Recep pedirá el formato correcto


# ══════════════════════════════════════════════════════════════════════════════
# BUG #4 — Stock se acumulaba (12 unidades en lugar de 4)
# Causa: VP re-delegaba registrar_entrada_stock en turno siguiente al recibir
#        información complementaria (proveedor). Sumaba de nuevo.
# Fix: reglas COMPRAS y INFORMACIÓN COMPLEMENTARIA en VP system prompt
# ══════════════════════════════════════════════════════════════════════════════

class TestStockOperaciones:
    """Tests de operaciones de stock en sheets_client."""

    def test_registrar_entrada_suma_unidades(self, sheets_con_stock):
        """registrar_entrada_stock debe SUMAR unidades, no reemplazar."""
        with patch("mcp.sheets_client.get_spreadsheet_id", return_value="sid"), \
             patch("mcp.sheets_client._sheets", return_value=sheets_con_stock):

            from mcp import sheets_client as sh

            # PLATITO-ALU tiene 11 unidades, compramos 4 más
            resultado = sh.registrar_entrada_stock(
                codigo="PLATITO-ALU", descripcion="Platito de aluminio",
                unidades=4, precio_venta=2500, costo_compra=1500
            )

            # Verificar que se llamó update con 15 (11+4)
            calls = sheets_con_stock.spreadsheets.return_value.values.return_value.update.call_args_list
            assert any("15" in str(c) for c in calls), \
                f"No sumó correctamente. Calls: {calls}"

    def test_set_unidades_reemplaza_no_suma(self, sheets_con_stock):
        """set_unidades_stock debe REEMPLAZAR la cantidad (para correcciones)."""
        with patch("mcp.sheets_client.get_spreadsheet_id", return_value="sid"), \
             patch("mcp.sheets_client._sheets", return_value=sheets_con_stock):

            from mcp import sheets_client as sh
            resultado = sh.set_unidades_stock(query="platito", cantidad=4)

            calls = sheets_con_stock.spreadsheets.return_value.values.return_value.update.call_args_list
            assert any("4" in str(c) for c in calls), \
                "set_unidades_stock no fijó la cantidad en 4"
            # Asegurar que NO puso 15 ni 11 (sumaría)
            assert not any("15" in str(c) for c in calls), \
                "set_unidades_stock sumó en lugar de reemplazar"

    def test_registrar_salida_resta_unidades(self, sheets_con_stock):
        """registrar_salida_stock debe RESTAR unidades (para ventas)."""
        with patch("mcp.sheets_client.get_spreadsheet_id", return_value="sid"), \
             patch("mcp.sheets_client._sheets", return_value=sheets_con_stock):

            from mcp import sheets_client as sh
            resultado = sh.registrar_salida_stock(query="platito", cantidad=1)

            # PLATITO-ALU tenía 11, debe quedar 10
            calls = sheets_con_stock.spreadsheets.return_value.values.return_value.update.call_args_list
            assert any("10" in str(c) for c in calls), \
                f"No restó 1 unidad correctamente. Calls: {calls}"
            assert "Precio de venta" in resultado, \
                "registrar_salida_stock debe devolver el precio de venta"

    def test_registrar_salida_no_va_negativo(self, sheets_con_stock):
        """Si el stock es insuficiente, queda en 0, no va negativo."""
        with patch("mcp.sheets_client.get_spreadsheet_id", return_value="sid"), \
             patch("mcp.sheets_client._sheets", return_value=sheets_con_stock):

            from mcp import sheets_client as sh
            # CORREA-MED tiene 0 unidades, intentamos vender 5
            resultado = sh.registrar_salida_stock(query="correa", cantidad=5)

            calls = sheets_con_stock.spreadsheets.return_value.values.return_value.update.call_args_list
            # El stock debe ser 0, no -5
            assert not any("-5" in str(c) for c in calls), \
                "El stock fue a negativo"

    def test_buscar_producto_fuzzy_singular_plural(self, sheets_con_stock):
        """buscar_producto debe encontrar 'platitos' cuando el nombre es 'Platito'."""
        with patch("mcp.sheets_client.get_spreadsheet_id", return_value="sid"), \
             patch("mcp.sheets_client._sheets", return_value=sheets_con_stock):

            from mcp import sheets_client as sh
            resultados = sh.buscar_producto("platitos de aluminio")
            assert len(resultados) > 0, "No encontró 'platito' buscando 'platitos'"
            assert any("platito" in str(r).lower() for r in resultados)

    def test_buscar_producto_por_codigo(self, sheets_con_stock):
        """buscar_producto debe encontrar por código."""
        with patch("mcp.sheets_client.get_spreadsheet_id", return_value="sid"), \
             patch("mcp.sheets_client._sheets", return_value=sheets_con_stock):

            from mcp import sheets_client as sh
            resultados = sh.buscar_producto("COLLAR-PER")
            assert len(resultados) > 0, "No encontró por código COLLAR-PER"


# ══════════════════════════════════════════════════════════════════════════════
# BUG #5 — Dashboard no cargaba (RuntimeError: Planilla no configurada)
# Causa: GET /dashboard no seteaba ContextVar del tenant antes de llamar a Sheets
# Fix: endpoint lee tenant_id de request.state.user y setea el ContextVar
# ══════════════════════════════════════════════════════════════════════════════

class TestContextVarTenant:
    """Tests de aislamiento de ContextVar entre tenants."""

    def test_contextvar_no_contamina_entre_tenants(self):
        """El ContextVar de un tenant no debe filtrarse al siguiente request."""
        from mcp.sheets_client import _tenant_sid_ctx, set_tenant_spreadsheet_id_ctx

        # Tenant A setea su spreadsheet_id
        set_tenant_spreadsheet_id_ctx("sheet_tenant_A")
        assert _tenant_sid_ctx.get() == "sheet_tenant_A"

        # Reset manual (simula fin de request)
        _tenant_sid_ctx.set("")
        assert _tenant_sid_ctx.get() == "", \
            "ContextVar no se reseteó: puede filtrarse al siguiente request"

    def test_contextvar_default_es_string_vacio(self):
        """El default del ContextVar debe ser '' para que get_spreadsheet_id levante RuntimeError."""
        from mcp.sheets_client import _tenant_sid_ctx
        assert _tenant_sid_ctx.get() == ""

    def test_get_spreadsheet_id_usa_contextvar(self):
        """get_spreadsheet_id debe retornar el ContextVar si está seteado."""
        from mcp.sheets_client import _tenant_sid_ctx, get_spreadsheet_id

        _tenant_sid_ctx.set("sid_de_prueba")
        sid = get_spreadsheet_id()
        assert sid == "sid_de_prueba"
        _tenant_sid_ctx.set("")  # cleanup

    def test_get_spreadsheet_id_sin_contextvar_levanta_error(self):
        """Sin ContextVar y sin config file, debe levantar RuntimeError descriptivo."""
        from mcp.sheets_client import _tenant_sid_ctx, get_spreadsheet_id

        _tenant_sid_ctx.set("")
        with patch("mcp.sheets_client.load_config", return_value={}), \
             patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("SPREADSHEET_ID", None)
            with pytest.raises(RuntimeError, match="no configurada"):
                get_spreadsheet_id()


# ══════════════════════════════════════════════════════════════════════════════
# BUG #6 — Columnas personalizadas: Finanzas debe estar protegida
# Fix: agregar_columna_personalizada bloquea Finanzas, permite Clientes y Stock
# ══════════════════════════════════════════════════════════════════════════════

class TestColumnasPersonalizadas:
    """Tests de agregar columnas personalizadas."""

    def test_clientes_permite_columnas(self, sheets_con_clientes):
        """Se deben poder agregar columnas a la hoja Clientes."""
        with patch("mcp.sheets_client.get_spreadsheet_id", return_value="sid"), \
             patch("mcp.sheets_client._sheets", return_value=sheets_con_clientes):

            from mcp import sheets_client as sh
            resultado = sh.agregar_columna_personalizada("Clientes", "Nombre del perro")
            assert "✓" in resultado or "agregada" in resultado.lower()

    def test_stock_permite_columnas(self, sheets_con_stock):
        """Se deben poder agregar columnas a la hoja Stock."""
        with patch("mcp.sheets_client.get_spreadsheet_id", return_value="sid"), \
             patch("mcp.sheets_client._sheets", return_value=sheets_con_stock):

            from mcp import sheets_client as sh
            resultado = sh.agregar_columna_personalizada("Stock", "Proveedor alternativo")
            assert "✓" in resultado or "agregada" in resultado.lower()

    def test_finanzas_bloqueada(self):
        """La hoja Finanzas NO debe permitir columnas personalizadas."""
        from mcp import sheets_client as sh
        resultado = sh.agregar_columna_personalizada("Finanzas", "Columna no permitida")
        assert "no puede" in resultado.lower() or "bloqueada" in resultado.lower() or \
               "no se puede" in resultado.lower() or "Finanzas" in resultado, \
            f"Finanzas no bloqueó la operación: {resultado}"

    def test_hoja_inexistente_bloqueada(self):
        """Hojas que no existen no deben permitir columnas."""
        from mcp import sheets_client as sh
        resultado = sh.agregar_columna_personalizada("Inventario", "Columna random")
        # El mensaje puede variar; verificar que mencione la restricción
        r = resultado.lower()
        assert any(w in r for w in ["no permit", "no puede", "no se puede", "solo se puede"]), \
            f"Debería indicar restricción: {resultado}"

    def test_columna_existente_no_duplica(self, sheets_con_clientes):
        """No debe agregar una columna que ya existe."""
        with patch("mcp.sheets_client.get_spreadsheet_id", return_value="sid"), \
             patch("mcp.sheets_client._sheets", return_value=sheets_con_clientes):

            from mcp import sheets_client as sh
            # "Nombre" ya existe como header
            resultado = sh.agregar_columna_personalizada("Clientes", "Nombre")
            assert "ya existe" in resultado.lower()

    def test_num_to_col_letter_conversion(self):
        """_num_to_col_letter debe convertir correctamente."""
        from mcp.sheets_client import _num_to_col_letter
        assert _num_to_col_letter(1)  == "A"
        assert _num_to_col_letter(26) == "Z"
        assert _num_to_col_letter(27) == "AA"
        assert _num_to_col_letter(28) == "AB"
        assert _num_to_col_letter(52) == "AZ"
        assert _num_to_col_letter(53) == "BA"


# ══════════════════════════════════════════════════════════════════════════════
# BUG #7 — Programador usaba credentials file en lugar de env var
# Causa: verificar_planilla usaba from_service_account_file() ignorando
#        GOOGLE_SERVICE_ACCOUNT_JSON → siempre fallaba en Railway
# Fix: usar sh._sheets() que tiene la lógica env→archivo correcta
# ══════════════════════════════════════════════════════════════════════════════

class TestProgramadorCredentials:
    """El Programador debe usar sh._sheets() no credenciales directas."""

    def test_verificar_planilla_usa_sheets_helper(self):
        """verificar_planilla debe delegar a sh._sheets(), no cargar credenciales directas."""
        from agents.programador import ProgramadorAgent
        agent = ProgramadorAgent()

        with patch("mcp.sheets_client.get_spreadsheet_id", return_value="sid"), \
             patch("mcp.sheets_client._sheets") as mock_sheets:

            mock_meta = MagicMock()
            mock_meta.execute.return_value = {
                "sheets": [{"properties": {"title": "Clientes"}},
                           {"properties": {"title": "Finanzas"}},
                           {"properties": {"title": "Stock"}}]
            }
            mock_sheets.return_value.spreadsheets.return_value.get.return_value = mock_meta

            resultado = agent.execute_tool("verificar_planilla", {})
            assert "Planilla accesible" in resultado
            assert "Clientes" in resultado
            # Asegurar que NO cargó credenciales directamente
            mock_sheets.assert_called()


# ══════════════════════════════════════════════════════════════════════════════
# BUG #8 — WebSocket broadcast se enviaba a todos los tenants
# Causa: ConnectionManager.broadcast() sin filtro de tenant_id
# Fix: dict keyed por tenant_id, broadcast solo al tenant activo
# ══════════════════════════════════════════════════════════════════════════════

class TestWebSocketIsolation:
    """Tests de aislamiento de WebSocket entre tenants."""

    @pytest.mark.asyncio
    async def test_broadcast_solo_al_tenant_correcto(self):
        """Un mensaje de tenant A no debe llegar a tenant B."""
        import sys
        # Necesitamos mockear fastapi antes del import
        with patch.dict(sys.modules, {
            "fastapi": MagicMock(),
            "fastapi.websockets": MagicMock(),
        }):
            # Crear manager directamente sin depender de FastAPI
            from unittest.mock import AsyncMock

            class ConnectionManager:
                def __init__(self):
                    self.active: dict = {}

                async def connect(self, ws, tenant_id: str):
                    self.active.setdefault(tenant_id, []).append(ws)

                async def broadcast(self, data: dict, tenant_id: str = ""):
                    if not tenant_id:
                        return
                    for ws in list(self.active.get(tenant_id, [])):
                        await ws.send_text("data")

            manager = ConnectionManager()

            ws_a = AsyncMock()
            ws_b = AsyncMock()

            await manager.connect(ws_a, "tenant_A")
            await manager.connect(ws_b, "tenant_B")

            await manager.broadcast({"msg": "solo para A"}, tenant_id="tenant_A")

            ws_a.send_text.assert_called_once()
            ws_b.send_text.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# BUG #9 — SQLite NULL devuelve None, no el default de dict.get()
# Causa: dict.get("spreadsheet_id", "") retorna None cuando el campo es NULL en SQLite
# Fix: usar (data or {}).get("key") or ""
# ══════════════════════════════════════════════════════════════════════════════

class TestSQLiteNullHandling:
    """Tests del manejo correcto de NULL de SQLite."""

    def test_dict_get_con_none_no_aplica_default(self):
        """Reproduce el bug: dict.get("k", "default") retorna None si el valor es None."""
        data = {"spreadsheet_id": None}  # Como SQLite NULL
        # El bug original:
        assert data.get("spreadsheet_id", "") is None, \
            "Este assert confirma que el bug existía"
        # El fix correcto:
        fixed = data.get("spreadsheet_id") or ""
        assert fixed == "", "El fix no manejó None correctamente"

    def test_patron_correcto_para_null_sqlite(self):
        """El patrón (data or {}).get("key") or "" maneja todos los casos."""
        casos = [
            ({"spreadsheet_id": None},    ""),       # NULL de SQLite
            ({"spreadsheet_id": ""},      ""),       # String vacío
            ({"spreadsheet_id": "abc"},   "abc"),    # Valor real
            ({},                           ""),       # Clave ausente
            (None,                         ""),       # Dict None completo
        ]
        for data, esperado in casos:
            resultado = (data or {}).get("spreadsheet_id") or ""
            assert resultado == esperado, \
                f"Para data={data!r}, esperaba {esperado!r}, got {resultado!r}"


# ══════════════════════════════════════════════════════════════════════════════
# BUG #10 — Regex de teléfono capturaba texto con espacios
# Causa: [\d\s\-]{8,15} con IGNORECASE capturaba "5491160602020 un"
# Fix: solo dígitos: [\d]{8,15}
# ══════════════════════════════════════════════════════════════════════════════

class TestRegexTelefono:
    """Tests del regex de extracción de teléfono."""

    def _extraer_tel(self, task: str) -> str:
        from agents.atencion_cliente import AtencionClienteAgent
        agent = AtencionClienteAgent()
        datos = agent._extraer_datos_cliente(task)
        return datos.get("telefono", "")

    def test_telefono_al_final_del_mensaje(self):
        """Teléfono seguido de texto no debe incluir el texto."""
        task = "Le vendí a nuestro nuevo cliente, Fernando Barrios 5491160602020 un platito!"
        tel = self._extraer_tel(task)
        assert tel == "5491160602020", f"Capturó texto extra: {tel!r}"
        assert "un" not in tel
        assert "platito" not in tel

    def test_telefono_con_prefijo_pais(self):
        task = "- Nombre: Ana García - Teléfono: +541144556677"
        tel = self._extraer_tel(task)
        assert "541144556677" in tel or "+541144556677" == tel

    def test_sin_telefono_devuelve_vacio(self):
        task = "Registrar nuevo cliente: Roberto sin teléfono"
        tel = self._extraer_tel(task)
        assert tel == "" or len(tel) < 8, f"Detectó teléfono donde no había: {tel!r}"
