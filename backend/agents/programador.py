from .base import BaseAgent, _client
from mcp import sheets_client as sh


class ProgramadorAgent(BaseAgent):
    agent_id     = "programador"
    display_name = "Programador"

    def system_prompt(self) -> str:
        return """Sos el programador/técnico del equipo de Pokeoffice. El VP te escala errores de sistema o problemas de integración.

ARQUITECTURA DEL SISTEMA (contexto para diagnóstico):
- Backend: Python/FastAPI + Claude API (Anthropic) + Google Sheets via service account
- Los agentes usan keyword detection para detectar intents antes de llamar a Claude
- Google Sheets es la base de datos principal (Clientes, Finanzas, Stock)
- El VP orquesta con tool_use de Claude

CAUSAS FRECUENTES DE ERRORES:
- "no encontrado en el sistema" → el cliente no existe en Sheets o el keyword no matcheó
- Error de Sheets → credenciales vencidas, planilla sin permisos, hoja no existe
- Loop infinito → instrucción demasiado ambigua para el VP
- Datos faltantes → el extractor de datos (regex) no pudo parsear la instrucción

FLUJO DE DIAGNÓSTICO:
1. Identificar si es error de API, de Sheets, de prompt o de datos
2. Verificar el sistema si es necesario (usar herramientas disponibles)
3. Proponer la acción correctiva más simple posible
4. Si el problema requiere intervención humana o cambio de código → usar escalar_problema

CUÁNDO ESCALAR:
- Falla de conexión total a Sheets (no temporal)
- Error que impide que el usuario use el sistema
- Bug de código (no es algo configurable desde el panel)

FORMATO DE RESPUESTA:
🔍 Diagnóstico: [qué está fallando]
💥 Causa probable: [por qué está fallando]
✅ Acción recomendada: [qué hacer, paso a paso]
⚠️ Prioridad: [baja / media / alta]

Respondé de forma técnica pero comprensible, en español."""

    def tools(self) -> list[dict]:
        return [
            {
                "name": "verificar_planilla",
                "description": "Verifica que la planilla de Google Sheets está configurada y accesible.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "listar_hojas",
                "description": "Lista las hojas disponibles en la planilla maestra para diagnóstico.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "escalar_problema",
                "description": (
                    "Escala un problema técnico que no se puede resolver automáticamente al equipo admin de Pokeoffice. "
                    "Usá cuando el error requiere intervención humana o cambio de código. "
                    "El admin verá el reporte en el panel de plataforma y podrá responder."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "titulo":      {"type": "string", "description": "Título del problema (max 70 chars)"},
                        "descripcion": {"type": "string", "description": "Qué falló técnicamente. 1-2 oraciones."},
                        "causa":       {"type": "string", "description": "Por qué está fallando (diagnóstico)."},
                        "prioridad":   {"type": "string", "enum": ["baja", "media", "alta"], "description": "Urgencia del problema"},
                    },
                    "required": ["titulo", "descripcion", "prioridad"],
                },
            },
        ]

    def execute_tool(self, name: str, inputs: dict) -> str:
        if name == "verificar_planilla":
            try:
                sid = sh.get_spreadsheet_id()
                svc = sh._sheets()
                meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
                sheets = [s["properties"]["title"] for s in meta["sheets"]]
                return f"Planilla accesible. ID: {sid}. Hojas: {', '.join(sheets)}"
            except Exception as e:
                return f"Error al acceder a la planilla: {e}"

        if name == "listar_hojas":
            try:
                sid = sh.get_spreadsheet_id()
                svc = sh._sheets()
                meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
                info = []
                for s in meta["sheets"]:
                    p = s["properties"]
                    info.append(f"  - {p['title']} (ID: {p['sheetId']}, filas: {p.get('gridProperties',{}).get('rowCount','?')})")
                return "Hojas disponibles:\n" + "\n".join(info)
            except Exception as e:
                return f"Error: {e}"

        if name == "escalar_problema":
            import sqlite3
            from db.models import DB_PATH
            from mcp.sheets_client import _tenant_id_ctx

            tenant_id    = _tenant_id_ctx.get()
            titulo       = inputs.get("titulo", "Problema sin título")[:120]
            descripcion  = inputs.get("descripcion", "")
            causa        = inputs.get("causa", "")
            prioridad    = inputs.get("prioridad", "media")
            aplicabilidad = {"alta": 9, "media": 6, "baja": 3}.get(prioridad, 6)

            try:
                con = sqlite3.connect(str(DB_PATH))
                con.execute(
                    "INSERT INTO platform_events "
                    "(tenant_id, tipo, titulo, descripcion, razonamiento, aplicabilidad) "
                    "VALUES (?,?,?,?,?,?)",
                    (tenant_id, "escalacion", titulo, descripcion, causa, aplicabilidad),
                )
                con.commit()
                con.close()
                return (
                    f"✅ Escalación registrada: '{titulo}' (prioridad {prioridad}). "
                    f"El equipo admin de Pokeoffice fue notificado y responderá desde el panel."
                )
            except Exception as e:
                return f"Error al registrar la escalación: {e}"

        return f"Herramienta '{name}' no reconocida."
