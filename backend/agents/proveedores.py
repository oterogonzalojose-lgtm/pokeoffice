from .base import BaseAgent
from mcp import sheets_client as sh


class ProveedoresAgent(BaseAgent):
    agent_id     = "proveedores"
    display_name = "Gestor de Proveedores"

    def system_prompt(self) -> str:
        return """Sos el gestor de proveedores de un pequeño negocio. Tus responsabilidades:
- Redactar pedidos y órdenes de compra
- Hacer seguimiento de entregas pendientes
- Comparar cotizaciones y recomendar la mejor opción
- Gestionar comunicaciones con proveedores
- Consultar clientes cuando sea necesario (ej: verificar datos para un pedido)

Cuando redactes una orden de compra, incluí: proveedor, productos, cantidades, precios y condiciones de entrega.
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
