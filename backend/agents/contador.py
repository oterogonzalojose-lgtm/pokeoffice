from .base import BaseAgent
from mcp import sheets_client as sh


class ContadorAgent(BaseAgent):
    agent_id     = "contador"
    display_name = "Contador"

    def system_prompt(self) -> str:
        return """Sos el contador de un pequeño negocio o emprendimiento argentino. Tus responsabilidades:
- Registrar ingresos y egresos en el libro contable
- Actualizar activos y pasivos del balance
- Actualizar posiciones bancarias en el cashflow
- Analizar la situación financiera y dar recomendaciones
- Generar resúmenes simples y claros

Cuando uses herramientas, interpretá los resultados y explicalos en lenguaje accesible.
Usá formato $ para montos. Siempre indicá si la situación es positiva o requiere atención.
Respondé siempre en español."""

    def tools(self) -> list[dict]:
        return [
            {
                "name": "registrar_movimiento",
                "description": "Registra un movimiento en el Libro Contable (debe/haber).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "descripcion": {"type": "string",  "description": "Descripción del movimiento"},
                        "debe":        {"type": "number",  "description": "Monto en el debe (egreso/deuda)"},
                        "haber":       {"type": "number",  "description": "Monto en el haber (ingreso/cobro)"},
                        "categoria":   {"type": "string",  "description": "Categoría (ej: Ventas, Sueldos, Alquiler)"},
                        "fecha":       {"type": "string",  "description": "Fecha en formato DD/MM/YYYY (opcional, usa hoy si no se indica)"},
                    },
                    "required": ["descripcion"],
                },
            },
            {
                "name": "obtener_resumen_contable",
                "description": "Lee el resumen del Libro Contable: Total Activos, Total Pasivos y Patrimonio Neto.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "actualizar_activo_pasivo",
                "description": "Actualiza el valor de un ítem del balance (activo o pasivo).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "tipo":        {"type": "string", "description": "'activo' o 'pasivo'"},
                        "descripcion": {"type": "string", "description": "Nombre exacto del ítem (ej: 'Inventario / stock')"},
                        "monto":       {"type": "number", "description": "Nuevo valor"},
                    },
                    "required": ["tipo", "descripcion", "monto"],
                },
            },
            {
                "name": "obtener_cashflow",
                "description": "Lee las posiciones bancarias y la liquidez total del negocio.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "actualizar_posicion_bancaria",
                "description": "Actualiza el saldo de una cuenta bancaria o de efectivo.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "cuenta": {"type": "string", "description": "Nombre de la cuenta (ej: 'Efectivo en caja', 'Banco (cuenta corriente)', 'Mercado Pago / billetera')"},
                        "saldo":  {"type": "number", "description": "Saldo actual en pesos"},
                    },
                    "required": ["cuenta", "saldo"],
                },
            },
            {
                "name": "registrar_movimiento_cashflow",
                "description": "Registra un ingreso o egreso en el flujo de caja.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "descripcion": {"type": "string", "description": "Descripción del movimiento"},
                        "ingreso":     {"type": "number", "description": "Monto ingresado"},
                        "egreso":      {"type": "number", "description": "Monto egresado"},
                        "fecha":       {"type": "string", "description": "Fecha DD/MM/YYYY (opcional)"},
                    },
                    "required": ["descripcion"],
                },
            },
        ]

    def execute_tool(self, name: str, inputs: dict) -> str:
        if name == "registrar_movimiento":
            return sh.registrar_movimiento(**inputs)

        if name == "obtener_resumen_contable":
            r = sh.obtener_resumen_contable()
            return (
                f"Activos: ${r['total_activos']:,.2f} | "
                f"Pasivos: ${r['total_pasivos']:,.2f} | "
                f"Patrimonio Neto: ${r['patrimonio_neto']:,.2f} | "
                f"Movimientos registrados: {r['movimientos_count']}"
            )

        if name == "actualizar_activo_pasivo":
            return sh.actualizar_activo_pasivo(**inputs)

        if name == "obtener_cashflow":
            cf = sh.obtener_cashflow()
            lines = [f"  • {c['cuenta']}: ${c['saldo']:,.2f}" for c in cf["cuentas"]]
            return f"Posiciones bancarias:\n" + "\n".join(lines) + f"\n\nLiquidez total: ${cf['total_liquidez']:,.2f}"

        if name == "actualizar_posicion_bancaria":
            return sh.actualizar_posicion_bancaria(**inputs)

        if name == "registrar_movimiento_cashflow":
            return sh.registrar_movimiento_cashflow(**inputs)

        return f"Herramienta '{name}' no reconocida."
