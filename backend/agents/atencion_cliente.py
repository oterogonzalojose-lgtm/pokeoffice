from .base import BaseAgent
from mcp import sheets_client as sh


class AtencionClienteAgent(BaseAgent):
    agent_id     = "atencion_cliente"
    display_name = "Recepcionista"

    def system_prompt(self) -> str:
        return """Sos la recepcionista de un pequeño negocio. Tus responsabilidades:
- Agregar y consultar clientes en la base de datos
- Redactar mensajes para clientes (WhatsApp, email, etc.)
- Gestionar avisos de turnos, horarios y novedades
- Mantener el CRM actualizado

Cuando usés una herramienta, interpretá el resultado y respondé de forma clara y útil.
Si vas a agregar un cliente, asegurate de tener al menos el nombre.
Cuando produzcas un mensaje listo para enviar, marcalo como "MENSAJE PARA CLIENTE:".
Respondé siempre en español."""

    def tools(self) -> list[dict]:
        return [
            {
                "name": "agregar_cliente",
                "description": "Agrega un nuevo cliente al Google Sheet de Clientes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "nombre":       {"type": "string",  "description": "Nombre del cliente"},
                        "apellido":     {"type": "string",  "description": "Apellido"},
                        "telefono":     {"type": "string",  "description": "Teléfono o WhatsApp"},
                        "email":        {"type": "string",  "description": "Email"},
                        "comentarios":  {"type": "string",  "description": "Notas adicionales"},
                    },
                    "required": ["nombre"],
                },
            },
            {
                "name": "listar_clientes",
                "description": "Lee la lista completa de clientes del Google Sheet.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "buscar_cliente",
                "description": "Busca un cliente por nombre, apellido, teléfono o email.",
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
        if name == "agregar_cliente":
            return sh.agregar_cliente(**inputs)
        if name == "listar_clientes":
            clientes = sh.listar_clientes()
            if not clientes:
                return "No hay clientes registrados aún."
            lines = [f"#{c['id']} {c['nombre']} {c['apellido']} — Tel: {c['telefono']} | Email: {c['email']}" for c in clientes]
            return f"{len(clientes)} clientes:\n" + "\n".join(lines)
        if name == "buscar_cliente":
            found = sh.buscar_cliente(inputs["query"])
            if not found:
                return f"No se encontró ningún cliente con '{inputs['query']}'."
            lines = [f"#{c['id']} {c['nombre']} {c['apellido']} — Tel: {c['telefono']} | Email: {c['email']} | {c['comentarios']}" for c in found]
            return "\n".join(lines)
        return f"Herramienta '{name}' no reconocida."
