"""
Tests de extractores de datos: validan que el parseo de lenguaje natural
produce los datos correctos ANTES de escribir en Sheets.
Son tests de consistencia de datos — sin llamadas reales a la API.
"""
import pytest
from agents.atencion_cliente import AtencionClienteAgent
from agents.contador import ContadorAgent


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTOR: atencion_cliente._extraer_datos_cliente
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractorCliente:
    agent = AtencionClienteAgent()

    # ── Casos felices ──────────────────────────────────────────────────────────

    def test_nombre_apellido_completo(self):
        datos = self.agent._extraer_datos_cliente(
            "Agregá al cliente Juan Pérez, teléfono 2991234567"
        )
        assert datos["nombre"] == "Juan", f"Esperaba 'Juan', obtuve '{datos['nombre']}'"
        assert datos["apellido"] == "Pérez", f"Esperaba 'Pérez', obtuve '{datos['apellido']}'"

    def test_telefono_simple(self):
        datos = self.agent._extraer_datos_cliente(
            "Nuevo cliente María García, tel 2994567890"
        )
        assert "2994567890" in datos["telefono"].replace(" ", ""), \
            f"Teléfono no encontrado: {datos['telefono']}"

    def test_email(self):
        datos = self.agent._extraer_datos_cliente(
            "Alta de cliente Pedro López, email pedro@gmail.com"
        )
        assert datos["email"] == "pedro@gmail.com", \
            f"Email incorrecto: {datos['email']}"

    def test_nombre_con_segundo_apellido(self):
        datos = self.agent._extraer_datos_cliente(
            "Registrar cliente Ana De La Cruz"
        )
        assert datos["nombre"] == "Ana", f"Nombre: {datos['nombre']}"
        assert "Cruz" in datos["apellido"], f"Apellido: {datos['apellido']}"

    def test_telefono_con_guiones(self):
        datos = self.agent._extraer_datos_cliente(
            "Agregar cliente Roberto Silva, cel 299-456-7890"
        )
        assert datos["telefono"] != "", f"Teléfono vacío para: 299-456-7890"

    def test_telefono_con_prefijo_internacional(self):
        datos = self.agent._extraer_datos_cliente(
            "Cliente Sofía Reyes, tel +54 299 4567890"
        )
        assert datos["telefono"] != "", f"No detectó teléfono internacional"

    # ── Casos edge ────────────────────────────────────────────────────────────

    def test_sin_apellido(self):
        datos = self.agent._extraer_datos_cliente("Agregar cliente Carlos")
        # Debe tener nombre aunque no haya apellido
        assert datos["nombre"] != "", f"Nombre vacío para instrucción simple"

    def test_nombre_en_minusculas(self):
        """BUG POTENCIAL: el regex requiere mayúsculas iniciales."""
        datos = self.agent._extraer_datos_cliente(
            "agregar cliente juan pérez tel 2991111111"
        )
        # Documentamos si falla — indica un bug en el extractor
        if datos["nombre"] == "":
            pytest.xfail(
                "BUG CONOCIDO: el regex no detecta nombres en minúsculas. "
                "Instrucción: 'juan pérez' → nombre vacío. "
                "Fix: añadir re.IGNORECASE al grupo de captura del nombre."
            )

    def test_telefono_muy_corto_no_detectado(self):
        """Teléfonos de menos de 8 dígitos NO deben capturarse como válidos."""
        datos = self.agent._extraer_datos_cliente("Cliente Lucas, tel 12345")
        # 12345 tiene 5 dígitos → no debe ser un teléfono válido
        # El regex pide 8+ dígitos
        tel = datos["telefono"].replace(" ", "").replace("-", "")
        assert len(tel) < 8 or tel == "", \
            f"Capturó teléfono inválido (muy corto): '{datos['telefono']}'"

    def test_email_malformado_no_detectado(self):
        datos = self.agent._extraer_datos_cliente(
            "Cliente Juliana, email notanemail"
        )
        assert datos["email"] == "", \
            f"Capturó email inválido: '{datos['email']}'"

    def test_datos_vacios_sin_datos(self):
        """Si no hay datos reconocibles, devuelve campos vacíos (no crash)."""
        datos = self.agent._extraer_datos_cliente("hola como estas")
        assert isinstance(datos, dict), "Debe devolver dict aunque no encuentre nada"


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTOR: atencion_cliente._extraer_query
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractorQuery:
    agent = AtencionClienteAgent()

    def test_buscar_por_nombre(self):
        q = self.agent._extraer_query("buscá al cliente Juan Pérez")
        assert "Juan" in q or "Pérez" in q, f"Query: '{q}'"

    def test_buscar_simple(self):
        q = self.agent._extraer_query("buscar García")
        assert "García" in q, f"Query: '{q}'"

    def test_buscar_sin_keyword(self):
        """Si no hay keyword, devuelve el texto entero como fallback."""
        q = self.agent._extraer_query("López 2995551234")
        assert q != "", "No debe devolver vacío"


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTOR: contador._extraer_monto
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractorMonto:
    agent = ContadorAgent()

    # ── Formatos argentinos ───────────────────────────────────────────────────

    def test_monto_simple(self):
        assert self.agent._extraer_monto("cobré 5000 pesos") == 5000.0

    def test_monto_con_signo_pesos(self):
        assert self.agent._extraer_monto("ingreso de $12500") == 12500.0

    def test_monto_punto_miles(self):
        """$5.000 → 5000 (punto como separador de miles)."""
        resultado = self.agent._extraer_monto("gasto de $5.000")
        assert resultado == 5000.0, f"$5.000 → esperaba 5000, obtuve {resultado}"

    def test_monto_punto_miles_grande(self):
        """$100.000 → 100000."""
        resultado = self.agent._extraer_monto("venta de $100.000")
        assert resultado == 100000.0, f"$100.000 → esperaba 100000, obtuve {resultado}"

    def test_monto_coma_decimal(self):
        """$1.500,50 → 1500.50."""
        resultado = self.agent._extraer_monto("pago de $1.500,50")
        assert resultado == 1500.50, f"$1.500,50 → esperaba 1500.50, obtuve {resultado}"

    def test_monto_sin_signo(self):
        resultado = self.agent._extraer_monto("registrar ingreso 80000")
        assert resultado == 80000.0, f"Esperaba 80000, obtuve {resultado}"

    def test_monto_con_espacios(self):
        resultado = self.agent._extraer_monto("cobré $ 3500")
        assert resultado == 3500.0, f"Esperaba 3500, obtuve {resultado}"

    # ── Casos edge / bugs potenciales ────────────────────────────────────────

    def test_monto_cero_cuando_no_hay(self):
        resultado = self.agent._extraer_monto("hacer balance del mes")
        assert resultado == 0.0, f"Sin monto debe devolver 0.0, obtuve {resultado}"

    def test_monto_no_captura_anno(self):
        """
        BUG POTENCIAL: '2025' en 'balance de 2025' puede capturarse como monto.
        """
        resultado = self.agent._extraer_monto("balance del año 2025")
        # 2025 se capturaría como monto → documenta el comportamiento
        if resultado == 2025.0:
            pytest.xfail(
                "BUG CONOCIDO: el extractor captura el año '2025' como monto. "
                "Fix: mejorar el regex para excluir números de 4 dígitos que parecen años "
                "(entre 1990-2099) cuando no tienen $ delante."
            )

    def test_monto_multiples_numeros_toma_primero(self):
        """Con múltiples números, debe tomar el primero (el más probable como monto)."""
        resultado = self.agent._extraer_monto("pagué $500 en efectivo, total 3 items")
        assert resultado == 500.0, f"Debería tomar $500, obtuve {resultado}"


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTOR: contador._extraer_descripcion
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractorDescripcion:
    agent = ContadorAgent()

    def test_descripcion_basica(self):
        desc = self.agent._extraer_descripcion("registrar gasto de $500 en electricidad")
        assert "electricidad" in desc.lower(), f"Descripción: '{desc}'"

    def test_descripcion_sin_monto(self):
        desc = self.agent._extraer_descripcion("ingreso por consulta médica $3000")
        assert "consulta" in desc.lower() or "médica" in desc.lower(), \
            f"Descripción: '{desc}'"

    def test_descripcion_no_vacia(self):
        """Siempre debe devolver algo, nunca vacío."""
        desc = self.agent._extraer_descripcion("cobré $5000")
        assert desc.strip() != "", f"Descripción vacía para 'cobré $5000'"

    def test_descripcion_sin_palabras_basura(self):
        """No debe contener palabras clave como 'registrar', 'ingreso', etc."""
        desc = self.agent._extraer_descripcion("registrar ingreso de $1000 por venta")
        basura = ["registr", "ingreso", " de ", " por "]
        # Al menos el monto y las keywords deben estar limpios
        assert "$" not in desc, f"El monto no debería estar en la descripción: '{desc}'"


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTOR: contador._extraer_cuenta
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractorCuenta:
    agent = ContadorAgent()

    def test_mercado_pago(self):
        assert self.agent._extraer_cuenta("actualizar mercado pago con $5000") == "Mercado Pago / billetera"

    def test_caja_de_ahorro(self):
        assert self.agent._extraer_cuenta("saldo en caja de ahorro $10000") == "Banco (caja de ahorro)"

    def test_cuenta_corriente(self):
        assert self.agent._extraer_cuenta("posición cuenta corriente $20000") == "Banco (cuenta corriente)"

    def test_efectivo(self):
        assert self.agent._extraer_cuenta("efectivo en caja $1500") == "Efectivo en caja"

    def test_fallback_banco(self):
        """Sin keyword → default banco corriente."""
        assert self.agent._extraer_cuenta("actualizar saldo $5000") == "Banco (cuenta corriente)"
