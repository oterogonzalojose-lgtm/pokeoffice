from .base import BaseAgent
from mcp import sheets_client as sh


class ProveedoresAgent(BaseAgent):
    agent_id     = "proveedores"
    display_name = "Gestor de Proveedores"

    def system_prompt(self) -> str:
        return """Sos el gestor de proveedores de un pequeño negocio. Manejás compras, stock e inventario.

REGLAS CRÍTICAS:
1. NUNCA inventes precios, cantidades ni datos de proveedores. Si faltan, pedílos antes de actuar.
2. Para una orden de compra necesitás MÍNIMO: proveedor, producto, cantidad.
3. Si hay stock en el sistema, consultálo antes de sugerir compras para no duplicar pedidos.
4. Confirmá siempre qué quedó registrado y qué quedó pendiente.

FORMATO DE ORDEN DE COMPRA:
═══════════════════════════
ORDEN DE COMPRA — [fecha]
Proveedor: [nombre]
───────────────────────────
[Producto] x[cant] — $[precio u.] — Total: $[subtotal]
───────────────────────────
TOTAL: $[total general]
Condiciones: [pago/entrega si se indicaron]
═══════════════════════════

ACCIONES EN STOCK:
- Entrada de mercadería: confirmá producto, cantidad y precio unitario registrado
- Stock bajo: indicá nombre, stock actual y cantidad sugerida de reposición

NO hagas:
- No generes órdenes sin proveedor + producto + cantidad como mínimo
- No modifiques stock sin datos concretos
- No inventes proveedores ni precios

Respondé siempre en español."""

    def tools(self) -> list[dict]:
        return [
            {
                "name": "listar_clientes",
                "description": "Consulta la lista de clientes (útil para verificar datos de contacto en pedidos).",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "buscar_cliente",
                "description": "Busca un cliente específico por nombre, teléfono o email.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Texto a buscar"}
                    },
                    "required": ["query"],
                },
            },
        ]

    def execute_tool(self, name: str, inputs: dict) -> str:
        if name == "listar_clientes":
            clientes = sh.listar_clientes()
            if not clientes:
                return "No hay clientes registrados."
            return "\n".join([f"#{c['id']} {c['nombre']} {c['apellido']} — {c['telefono']}" for c in clientes])
        if name == "buscar_cliente":
            found = sh.buscar_cliente(inputs["query"])
            if not found:
                return f"No se encontró '{inputs['query']}'."
            return "\n".join([f"#{c['id']} {c['nombre']} {c['apellido']} — Tel: {c['telefono']} | Email: {c['email']}" for c in found])
        return f"Herramienta '{name}' no reconocida."
