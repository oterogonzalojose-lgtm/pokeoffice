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
- Google Sheets es la base de datos principal (Clientes, Cashflow, Libro Contable, Stock)
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
4. Indicar si el problema es temporal (reintentable) o requiere configuración

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
        ]

    def execute_tool(self, name: str, inputs: dict) -> str:
        if name == "verificar_planilla":
            try:
                sid = sh.get_spreadsheet_id()
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                import os
                creds_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "./credentials.json")
                creds = service_account.Credentials.from_service_account_file(
                    creds_path,
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
                svc = build("sheets", "v4", credentials=creds)
                meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
                sheets = [s["properties"]["title"] for s in meta["sheets"]]
                return f"Planilla accesible. ID: {sid}. Hojas: {', '.join(sheets)}"
            except Exception as e:
                return f"Error al acceder a la planilla: {e}"

        if name == "listar_hojas":
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                import os
                sid = sh.get_spreadsheet_id()
                creds_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "./credentials.json")
                creds = service_account.Credentials.from_service_account_file(
                    creds_path,
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
                svc = build("sheets", "v4", credentials=creds)
                meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
                info = []
                for s in meta["sheets"]:
                    p = s["properties"]
                    info.append(f"  - {p['title']} (ID: {p['sheetId']}, filas: {p.get('gridProperties',{}).get('rowCount','?')})")
                return "Hojas disponibles:\n" + "\n".join(info)
            except Exception as e:
                return f"Error: {e}"

        return f"Herramienta '{name}' no reconocida."
