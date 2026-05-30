from .base import BaseAgent
from mcp import sheets_client as sh


class ProveedoresAgent(BaseAgent):
    agent_id     = "proveedores"
    display_name = "Gestor de Proveedores"

    def system_prompt(self) -> str:
        return """Sos el gestor de proveedores y del inventario de un pequeño negocio. Manejás compras, stock y precios.

REGLAS CRÍTICAS:
1. Si la instrucción tiene producto + precio, ejecutá directamente. No preguntes si ya existe — buscá primero y actualizá.
2. Para actualizar precio: usá `actualizar_precio_stock` con el nombre del producto tal como fue mencionado.
3. Para una orden de compra necesitás MÍNIMO: proveedor, producto, cantidad.
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
                "name": "registrar_entrada_stock",
                "description": (
                    "Registra la entrada de mercadería al inventario. "
                    "Usá cuando el jefe compra productos para el negocio. "
                    "Si el producto ya existe actualiza las unidades; si es nuevo lo crea."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "codigo":       {"type": "string",  "description": "Código corto del producto, ej: CORREA-PERRO"},
                        "descripcion":  {"type": "string",  "description": "Descripción completa del producto"},
                        "unidades":     {"type": "integer", "description": "Cantidad de unidades recibidas"},
                        "precio_venta": {"type": "number",  "description": "Precio de venta al público ($)"},
                        "costo_compra": {"type": "number",  "description": "Costo de compra unitario ($)"},
                        "proveedor":    {"type": "string",  "description": "Nombre del proveedor (opcional)"},
                        "stock_minimo": {"type": "integer", "description": "Stock mínimo antes de reponer (default: 5)"},
                    },
                    "required": ["codigo", "descripcion", "unidades"],
                },
            },
            {
                "name": "listar_stock",
                "description": "Consulta el inventario actual de productos con precios, unidades y proveedor.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "buscar_producto",
                "description": "Busca un producto en el stock por nombre o código.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Nombre o código a buscar"}
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "actualizar_precio_stock",
                "description": (
                    "Actualiza el precio de venta (y opcionalmente el costo) de un producto ya existente en el inventario. "
                    "Busca por nombre o código. Usá cuando el jefe quiere cambiar el precio de un producto."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query":        {"type": "string", "description": "Nombre o código del producto a actualizar"},
                        "precio_venta": {"type": "number", "description": "Nuevo precio de venta al público ($)"},
                        "costo_compra": {"type": "number", "description": "Nuevo costo de compra (opcional)"},
                    },
                    "required": ["query", "precio_venta"],
                },
            },
            {
                "name": "listar_clientes",
                "description": "Consulta la lista de clientes.",
                "input_schema": {"type": "object", "properties": {}},
            },
        ]

    def execute_tool(self, name: str, inputs: dict) -> str:
        if name == "registrar_entrada_stock":
            return sh.registrar_entrada_stock(
                codigo=inputs.get("codigo", ""),
                descripcion=inputs.get("descripcion", ""),
                unidades=int(inputs.get("unidades", 0)),
                precio_venta=float(inputs.get("precio_venta", 0)),
                costo_compra=float(inputs.get("costo_compra", 0)),
                proveedor=inputs.get("proveedor", ""),
                stock_minimo=int(inputs.get("stock_minimo", 5)),
            )
        if name == "listar_stock":
            items = sh.listar_stock()
            if not items:
                return "Stock vacío."
            return "\n".join([
                f"{p['codigo']} — {p['descripcion']} | {p['unidades']} u. | ${p['precio']}"
                for p in items
            ])
        if name == "buscar_producto":
            found = sh.buscar_producto(inputs["query"])
            if not found:
                return f"No se encontró '{inputs['query']}' en stock."
            return "\n".join([
                f"{p['codigo']} — {p['descripcion']} | {p['unidades']} u. | ${p['precio']}"
                for p in found
            ])
        if name == "actualizar_precio_stock":
            return sh.actualizar_precio_stock(
                query=inputs.get("query", ""),
                precio_venta=float(inputs.get("precio_venta", 0)),
                costo_compra=float(inputs.get("costo_compra", 0)),
            )
        if name == "listar_clientes":
            clientes = sh.listar_clientes()
            if not clientes:
                return "No hay clientes registrados."
            return "\n".join([f"#{c['id']} {c['nombre']} {c['apellido']} — {c['telefono']}" for c in clientes])
        return f"Herramienta '{name}' no reconocida."
