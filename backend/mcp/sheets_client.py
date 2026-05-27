"""
Google Sheets client — Planilla Maestra de Pokeoffice.

Estructura de la planilla:
  Sheet 1 — Clientes       : CRM básico
  Sheet 2 — Libro Contable : Activos / Pasivos + movimientos
  Sheet 3 — Cashflow       : Posiciones bancarias + flujo de caja
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_CONFIG_PATH = Path(__file__).parent.parent / "pokeoffice.config.json"


# ── Credentials & config ──────────────────────────────────────────────────────

def _creds():
    path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "./credentials.json")
    return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)


def _sheets():
    return build("sheets", "v4", credentials=_creds())


def _drive():
    return build("drive", "v3", credentials=_creds())


def load_config() -> dict:
    if _CONFIG_PATH.exists():
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def save_config(data: dict):
    cfg = load_config()
    cfg.update(data)
    _CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def get_spreadsheet_id() -> str:
    sid = load_config().get("spreadsheet_id") or os.getenv("SPREADSHEET_ID", "")
    if not sid:
        raise RuntimeError(
            "Planilla maestra no configurada. "
            "Ejecutá: python scripts/crear_planilla.py --nombre 'Mi Negocio'"
        )
    return sid


# ── Sheet creation ─────────────────────────────────────────────────────────────

def crear_planilla_maestra(nombre_negocio: str) -> str:
    """
    Crea la planilla maestra con las 3 hojas preconfiguradas.
    Devuelve el spreadsheet_id para guardar en config.
    """
    svc = _sheets()
    drv = _drive()

    # Create spreadsheet skeleton
    body = {
        "properties": {"title": f"{nombre_negocio} — Planilla Maestra Pokeoffice"},
        "sheets": [
            {"properties": {"title": "Clientes",       "index": 0, "tabColor": {"red": 0.18, "green": 0.68, "blue": 0.38}}},
            {"properties": {"title": "Libro Contable", "index": 1, "tabColor": {"red": 0.95, "green": 0.61, "blue": 0.07}}},
            {"properties": {"title": "Cashflow",       "index": 2, "tabColor": {"red": 0.29, "green": 0.56, "blue": 0.89}}},
        ],
    }
    result = svc.spreadsheets().create(body=body, fields="spreadsheetId").execute()
    sid = result["spreadsheetId"]

    _setup_clientes(svc, sid)
    _setup_libro_contable(svc, sid)
    _setup_cashflow(svc, sid)
    _apply_formats(svc, sid)

    # Make it accessible to anyone with link (so the owner can open it)
    drv.permissions().create(
        fileId=sid,
        body={"type": "anyone", "role": "writer"},
    ).execute()

    save_config({"spreadsheet_id": sid, "business_name": nombre_negocio})
    return sid


def _setup_clientes(svc, sid: str):
    headers = [["#", "Nombre", "Apellido", "Teléfono", "Email", "Comentarios", "Fecha de Alta"]]
    _write(svc, sid, "Clientes!A1:G1", headers)


def _setup_libro_contable(svc, sid: str):
    rows = [
        ["LIBRO CONTABLE"],
        [],
        ["── ACTIVOS ──"],
        ["Descripción", "", "Monto ($)"],
        ["Caja y efectivo", "", 0],
        ["Cuentas bancarias", "", 0],
        ["Cuentas a cobrar", "", 0],
        ["Inventario / stock", "", 0],
        ["Otros activos", "", 0],
        ["TOTAL ACTIVOS", "", "=SUM(C5:C9)"],
        [],
        ["── PASIVOS ──"],
        ["Descripción", "", "Monto ($)"],
        ["Deudas a proveedores", "", 0],
        ["Préstamos / deudas bancarias", "", 0],
        ["Otros pasivos", "", 0],
        ["TOTAL PASIVOS", "", "=SUM(C14:C16)"],
        [],
        ["PATRIMONIO NETO", "", "=C10-C17"],
        [],
        [],
        ["── MOVIMIENTOS ──"],
        ["Fecha", "N°", "Descripción", "Debe ($)", "Haber ($)", "Saldo ($)", "Categoría"],
    ]
    _write(svc, sid, "Libro Contable!A1:G23", rows)


def _setup_cashflow(svc, sid: str):
    rows = [
        ["CASHFLOW / POSICIONES BANCARIAS"],
        [],
        ["── CUENTAS BANCARIAS Y EFECTIVO ──"],
        ["Cuenta / Banco", "Tipo", "Saldo ($)", "Última actualización"],
        ["Efectivo en caja", "Efectivo", 0, ""],
        ["Banco (cuenta corriente)", "Bancario", 0, ""],
        ["Banco (caja de ahorro)", "Bancario", 0, ""],
        ["Mercado Pago / billetera", "Digital", 0, ""],
        ["Otros", "Otro", 0, ""],
        ["TOTAL LIQUIDEZ", "", "=SUM(C5:C9)", ""],
        [],
        [],
        ["── MOVIMIENTOS DE CAJA ──"],
        ["Fecha", "Descripción", "Ingreso ($)", "Egreso ($)", "Saldo acumulado"],
    ]
    _write(svc, sid, "Cashflow!A1:E14", rows)


def _write(svc, sid: str, rng: str, values: list):
    svc.spreadsheets().values().update(
        spreadsheetId=sid,
        range=rng,
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()


def _apply_formats(svc, sid: str):
    """Bold headers and color title rows."""
    sheets_meta = _sheets().spreadsheets().get(spreadsheetId=sid).execute()
    sheet_ids = {s["properties"]["title"]: s["properties"]["sheetId"] for s in sheets_meta["sheets"]}

    requests = []
    for title, row, color in [
        ("Clientes",       0, {"red": 0.18, "green": 0.68, "blue": 0.38}),
        ("Libro Contable", 0, {"red": 0.95, "green": 0.61, "blue": 0.07}),
        ("Cashflow",       0, {"red": 0.29, "green": 0.56, "blue": 0.89}),
    ]:
        sid_sheet = sheet_ids[title]
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sid_sheet, "startRowIndex": row, "endRowIndex": row+1},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": color,
                    "textFormat": {"bold": True, "fontSize": 12},
                }},
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        })

    _sheets().spreadsheets().batchUpdate(
        spreadsheetId=sid, body={"requests": requests}
    ).execute()


# ── Clientes ──────────────────────────────────────────────────────────────────

def listar_clientes() -> list[dict]:
    sid = get_spreadsheet_id()
    result = _sheets().spreadsheets().values().get(
        spreadsheetId=sid, range="Clientes!A2:G"
    ).execute()
    rows = result.get("values", [])
    keys = ["id", "nombre", "apellido", "telefono", "email", "comentarios", "fecha_alta"]
    return [dict(zip(keys, row + [""] * (len(keys) - len(row)))) for row in rows if any(row)]


def agregar_cliente(nombre: str, apellido: str = "", telefono: str = "",
                    email: str = "", comentarios: str = "") -> str:
    sid = get_spreadsheet_id()
    clientes = listar_clientes()
    next_id = len(clientes) + 1
    fecha = datetime.now().strftime("%d/%m/%Y")
    row = [[next_id, nombre, apellido, telefono, email, comentarios, fecha]]
    _sheets().spreadsheets().values().append(
        spreadsheetId=sid, range="Clientes!A:G",
        valueInputOption="USER_ENTERED", body={"values": row},
    ).execute()
    return f"Cliente #{next_id} '{nombre} {apellido}' agregado correctamente."


def buscar_cliente(query: str) -> list[dict]:
    clientes = listar_clientes()
    q = query.lower()
    return [c for c in clientes if q in c.get("nombre","").lower()
            or q in c.get("apellido","").lower()
            or q in c.get("telefono","").lower()
            or q in c.get("email","").lower()]


# ── Libro Contable ────────────────────────────────────────────────────────────

def obtener_resumen_contable() -> dict:
    sid = get_spreadsheet_id()
    result = _sheets().spreadsheets().values().get(
        spreadsheetId=sid, range="Libro Contable!A1:G"
    ).execute()
    rows = result.get("values", [])
    # Extract totals from known rows (0-indexed: row 9 = Total Activos, row 16 = Total Pasivos, row 18 = Patrimonio)
    def safe(r, col=2):
        try: return float(str(rows[r][col]).replace(",",".").replace("$","").strip())
        except: return 0.0
    return {
        "total_activos":  safe(9),
        "total_pasivos":  safe(16),
        "patrimonio_neto": safe(18),
        "movimientos_count": max(0, len(rows) - 23),
    }


def registrar_movimiento(descripcion: str, debe: float = 0, haber: float = 0,
                          categoria: str = "", fecha: str = "") -> str:
    sid = get_spreadsheet_id()
    if not fecha:
        fecha = datetime.now().strftime("%d/%m/%Y")

    # Get current movements to calculate running balance and next N°
    result = _sheets().spreadsheets().values().get(
        spreadsheetId=sid, range="Libro Contable!A24:G"
    ).execute()
    movs = result.get("values", [])
    n = len(movs) + 1
    prev_saldo = 0.0
    if movs:
        try: prev_saldo = float(str(movs[-1][5]).replace(",",".").replace("$","").strip())
        except: pass
    saldo = prev_saldo + haber - debe
    row = [[fecha, n, descripcion, debe or "", haber or "", round(saldo, 2), categoria]]

    _sheets().spreadsheets().values().append(
        spreadsheetId=sid, range="Libro Contable!A:G",
        valueInputOption="USER_ENTERED", body={"values": row},
    ).execute()
    return f"Movimiento registrado: {descripcion} — Debe: ${debe} | Haber: ${haber} | Saldo: ${saldo:.2f}"


def actualizar_activo_pasivo(tipo: str, descripcion: str, monto: float) -> str:
    """
    tipo: 'activo' o 'pasivo'
    descripcion: nombre del item (ej: 'Inventario / stock')
    monto: valor nuevo
    """
    sid = get_spreadsheet_id()
    svc = _sheets()
    result = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Libro Contable!A1:C20"
    ).execute()
    rows = result.get("values", [])

    for i, row in enumerate(rows):
        if row and descripcion.lower() in str(row[0]).lower():
            rng = f"Libro Contable!C{i+1}"
            svc.spreadsheets().values().update(
                spreadsheetId=sid, range=rng,
                valueInputOption="USER_ENTERED",
                body={"values": [[monto]]},
            ).execute()
            return f"'{descripcion}' actualizado a ${monto:,.2f}"

    return f"No se encontró '{descripcion}' en el libro contable. Verificá el nombre exacto."


# ── Cashflow ──────────────────────────────────────────────────────────────────

def obtener_cashflow() -> dict:
    sid = get_spreadsheet_id()
    result = _sheets().spreadsheets().values().get(
        spreadsheetId=sid, range="Cashflow!A1:E"
    ).execute()
    rows = result.get("values", [])
    cuentas = []
    for row in rows[3:9]:  # rows 4-9 (0-indexed 3-8) = bank positions
        if row and len(row) >= 3:
            try:
                saldo = float(str(row[2]).replace(",",".").replace("$","").strip())
            except:
                saldo = 0.0
            cuentas.append({"cuenta": row[0] if row else "", "tipo": row[1] if len(row)>1 else "", "saldo": saldo})

    total = sum(c["saldo"] for c in cuentas)
    return {"cuentas": cuentas, "total_liquidez": total}


def actualizar_posicion_bancaria(cuenta: str, saldo: float) -> str:
    sid = get_spreadsheet_id()
    svc = _sheets()
    result = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Cashflow!A4:D9"
    ).execute()
    rows = result.get("values", [])

    for i, row in enumerate(rows):
        if row and cuenta.lower() in str(row[0]).lower():
            fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
            row_num = i + 4  # 1-indexed, starting at row 4
            svc.spreadsheets().values().update(
                spreadsheetId=sid, range=f"Cashflow!C{row_num}:D{row_num}",
                valueInputOption="USER_ENTERED",
                body={"values": [[saldo, fecha]]},
            ).execute()
            return f"Posición de '{cuenta}' actualizada a ${saldo:,.2f}"

    return f"Cuenta '{cuenta}' no encontrada. Opciones: Efectivo en caja, Banco (cuenta corriente), Banco (caja de ahorro), Mercado Pago / billetera, Otros."


def registrar_movimiento_cashflow(descripcion: str, ingreso: float = 0,
                                   egreso: float = 0, fecha: str = "") -> str:
    sid = get_spreadsheet_id()
    if not fecha:
        fecha = datetime.now().strftime("%d/%m/%Y")

    result = _sheets().spreadsheets().values().get(
        spreadsheetId=sid, range="Cashflow!A15:E"
    ).execute()
    movs = result.get("values", [])
    prev_saldo = 0.0
    if movs:
        try: prev_saldo = float(str(movs[-1][4]).replace(",",".").replace("$","").strip())
        except: pass
    saldo = prev_saldo + ingreso - egreso
    row = [[fecha, descripcion, ingreso or "", egreso or "", round(saldo, 2)]]

    _sheets().spreadsheets().values().append(
        spreadsheetId=sid, range="Cashflow!A:E",
        valueInputOption="USER_ENTERED", body={"values": row},
    ).execute()
    return f"Movimiento registrado: {descripcion} | Ingreso: ${ingreso} | Egreso: ${egreso} | Saldo: ${saldo:.2f}"


# ── Info general ──────────────────────────────────────────────────────────────

def get_spreadsheet_url() -> str:
    return f"https://docs.google.com/spreadsheets/d/{get_spreadsheet_id()}"
