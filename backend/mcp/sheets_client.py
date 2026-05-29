"""
Google Sheets client — Planilla Maestra de Pokeoffice.

Estructura de la planilla:
  Sheet 1 — Clientes       : CRM básico
  Sheet 2 — Libro Contable : Activos / Pasivos + movimientos
  Sheet 3 — Cashflow       : Posiciones bancarias + flujo de caja
  Sheet 4 — Stock          : Inventario de productos
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

_DATA_DIR    = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent)))
_CONFIG_PATH = _DATA_DIR / "pokeoffice.config.json"


# ── Credentials & config ──────────────────────────────────────────────────────

def _creds():
    # Prioridad 1: JSON completo en variable de entorno (Railway / producción)
    json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if json_str:
        info = json.loads(json_str)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    # Prioridad 2: archivo local (desarrollo)
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

def configurar_planilla_existente(sid: str, nombre_negocio: str = "Mi Negocio") -> str:
    """
    Configura un Google Sheet existente (ya compartido con la cuenta de servicio).
    Renombra la hoja por defecto y agrega Libro Contable y Cashflow.
    """
    svc = _sheets()

    # Get current sheets
    meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
    existing = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
    default_sheet_id = list(existing.values())[0]
    default_sheet_title = list(existing.keys())[0]

    requests = []

    # Rename first sheet to "Clientes" if needed
    if default_sheet_title != "Clientes":
        requests.append({"updateSheetProperties": {
            "properties": {"sheetId": default_sheet_id, "title": "Clientes",
                           "tabColor": {"red": 0.18, "green": 0.68, "blue": 0.38}},
            "fields": "title,tabColor",
        }})

    # Add missing sheets
    for title, color in [
        ("Libro Contable", {"red": 0.95, "green": 0.61, "blue": 0.07}),
        ("Cashflow",       {"red": 0.29, "green": 0.56, "blue": 0.89}),
        ("Stock",          {"red": 0.60, "green": 0.20, "blue": 0.80}),
    ]:
        if title not in existing:
            requests.append({"addSheet": {"properties": {
                "title": title, "tabColor": color,
            }}})

    if requests:
        svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": requests}).execute()

    # Now set up content for each sheet
    _setup_clientes(svc, sid)
    _setup_cashflow(svc, sid)        # primero cashflow (libro contable lo referencia)
    _setup_libro_contable(svc, sid)
    _setup_stock(svc, sid)
    _apply_formats(svc, sid)

    save_config({"spreadsheet_id": sid, "business_name": nombre_negocio})
    return sid


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
            {"properties": {"title": "Stock",          "index": 3, "tabColor": {"red": 0.60, "green": 0.20, "blue": 0.80}}},
        ],
    }
    result = svc.spreadsheets().create(body=body, fields="spreadsheetId").execute()
    sid = result["spreadsheetId"]

    _setup_clientes(svc, sid)
    _setup_cashflow(svc, sid)        # primero cashflow (libro contable lo referencia)
    _setup_libro_contable(svc, sid)
    _setup_stock(svc, sid)
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
    # C5 y C6 usan fórmulas que referencian Cashflow para mantener sincronía automática.
    # C8 referencia la hoja Stock para calcular valor del inventario.
    rows = [
        ["LIBRO CONTABLE"],
        [],
        ["── ACTIVOS ──"],
        ["Descripción", "", "Monto ($)"],
        ["Caja y efectivo",              "", "=Cashflow!C5"],
        ["Cuentas bancarias",            "", "=SUM(Cashflow!C6:C9)"],
        ["Cuentas a cobrar",             "", 0],
        ["Inventario / stock",           "", "=SUMPRODUCT(IFERROR(Stock!B2:B1000,0),IFERROR(Stock!C2:C1000,0))"],
        ["Otros activos",                "", 0],
        ["TOTAL ACTIVOS",                "", "=SUM(C5:C9)"],
        [],
        ["── PASIVOS ──"],
        ["Descripción", "", "Monto ($)"],
        ["Deudas a proveedores",          "", 0],
        ["Préstamos / deudas bancarias",  "", 0],
        ["Otros pasivos",                 "", 0],
        ["TOTAL PASIVOS",                 "", "=SUM(C14:C16)"],
        [],
        ["PATRIMONIO NETO",              "", "=C10-C17"],
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


def _setup_stock(svc, sid: str):
    headers = [["Código", "Unidades", "Precio ($)", "Promoción", "Descripción", "Última act."]]
    _write(svc, sid, "Stock!A1:F1", headers)


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


def briefing_cliente(query: str) -> dict:
    """
    Genera un briefing completo de un cliente cruzando su ficha con el stock disponible.
    Devuelve ficha del cliente + productos en stock con precio/promoción.
    """
    clientes = buscar_cliente(query)
    if not clientes:
        return {"error": f"No se encontró ningún cliente con '{query}'."}

    cliente = clientes[0]  # tomar el primero encontrado

    try:
        stock = listar_stock()
        productos_disponibles = [
            {
                "codigo":      p.get("codigo", ""),
                "descripcion": p.get("descripcion", ""),
                "unidades":    p.get("unidades", "0"),
                "precio":      p.get("precio", "0"),
                "promocion":   p.get("promocion", ""),
            }
            for p in stock
            if int(str(p.get("unidades", "0")).strip() or "0") > 0
        ]
    except Exception:
        productos_disponibles = []

    return {
        "cliente":    cliente,
        "stock":      productos_disponibles,
        "generado_el": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


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
                                   egreso: float = 0, fecha: str = "",
                                   cuenta: str = "Efectivo en caja") -> str:
    sid = get_spreadsheet_id()
    svc = _sheets()
    if not fecha:
        fecha = datetime.now().strftime("%d/%m/%Y")

    # Calcular saldo acumulado del log de movimientos
    result = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Cashflow!A15:E"
    ).execute()
    movs = result.get("values", [])
    prev_saldo = 0.0
    if movs:
        try: prev_saldo = float(str(movs[-1][4]).replace(",", ".").replace("$", "").strip())
        except: pass
    saldo = round(prev_saldo + ingreso - egreso, 2)
    row = [[fecha, descripcion, ingreso or "", egreso or "", saldo]]

    svc.spreadsheets().values().append(
        spreadsheetId=sid, range="Cashflow!A:E",
        valueInputOption="USER_ENTERED", body={"values": row},
    ).execute()

    # Actualizar la posición bancaria de la cuenta correspondiente
    # (esto hace que Libro Contable!C5/C6 se actualicen automáticamente via fórmula)
    try:
        pos_result = svc.spreadsheets().values().get(
            spreadsheetId=sid, range="Cashflow!A5:C9"
        ).execute()
        pos_rows = pos_result.get("values", [])
        for i, row_data in enumerate(pos_rows):
            if row_data and cuenta.lower() in str(row_data[0]).lower():
                saldo_actual = 0.0
                if len(row_data) > 2:
                    try:
                        saldo_actual = float(str(row_data[2]).replace(",", ".").replace("$", "").strip() or "0")
                    except:
                        saldo_actual = 0.0
                nuevo_saldo = round(saldo_actual + ingreso - egreso, 2)
                row_num = i + 5  # A5 es índice 0 → fila 5
                fecha_upd = datetime.now().strftime("%d/%m/%Y %H:%M")
                svc.spreadsheets().values().update(
                    spreadsheetId=sid,
                    range=f"Cashflow!C{row_num}:D{row_num}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [[nuevo_saldo, fecha_upd]]},
                ).execute()
                break
    except Exception:
        pass  # No bloquear si falla la actualización de posición

    return f"Movimiento registrado: {descripcion} | Ingreso: ${ingreso} | Egreso: ${egreso} | Saldo acum.: ${saldo:.2f}"


# ── Stock ─────────────────────────────────────────────────────────────────────

def listar_stock() -> list[dict]:
    """Lee stock incluyendo columnas extendidas: stock_minimo, costo_compra, proveedor, margen."""
    sid = get_spreadsheet_id()
    result = _sheets().spreadsheets().values().get(
        spreadsheetId=sid, range="Stock!A2:J"
    ).execute()
    rows = result.get("values", [])
    keys = ["codigo", "unidades", "precio", "promocion", "descripcion", "ultima_act",
            "stock_minimo", "costo_compra", "proveedor", "margen"]
    return [dict(zip(keys, row + [""] * (len(keys) - len(row)))) for row in rows if any(row)]


def agregar_producto(codigo: str, descripcion: str, unidades: int = 0,
                     precio: float = 0.0, promocion: str = "") -> str:
    sid = get_spreadsheet_id()
    fecha = datetime.now().strftime("%d/%m/%Y")
    row = [[codigo, unidades, precio, promocion, descripcion, fecha]]
    _sheets().spreadsheets().values().append(
        spreadsheetId=sid, range="Stock!A:F",
        valueInputOption="USER_ENTERED", body={"values": row},
    ).execute()
    return f"Producto '{codigo}' — {descripcion} agregado. Stock: {unidades} unidades a ${precio:.2f}."


def actualizar_unidades_stock(codigo: str, delta: int) -> str:
    """Suma o resta unidades del stock de un producto. delta puede ser negativo (venta)."""
    sid = get_spreadsheet_id()
    svc = _sheets()
    result = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Stock!A2:F"
    ).execute()
    rows = result.get("values", [])
    for i, row in enumerate(rows):
        if row and str(row[0]).lower() == codigo.lower():
            try:
                unidades_actuales = int(str(row[1]).strip() or "0")
            except:
                unidades_actuales = 0
            nuevas = max(0, unidades_actuales + delta)
            row_num = i + 2  # 1-indexed, starts at row 2
            fecha = datetime.now().strftime("%d/%m/%Y")
            svc.spreadsheets().values().update(
                spreadsheetId=sid,
                range=f"Stock!B{row_num}:F{row_num}",
                valueInputOption="USER_ENTERED",
                body={"values": [[nuevas, row[2] if len(row) > 2 else 0,
                                  row[3] if len(row) > 3 else "",
                                  row[4] if len(row) > 4 else "",
                                  fecha]]},
            ).execute()
            accion = "vendidas" if delta < 0 else "agregadas"
            return f"Stock '{codigo}': {unidades_actuales} → {nuevas} unidades ({abs(delta)} {accion})."
    return f"Producto con código '{codigo}' no encontrado en Stock."


def buscar_producto(query: str) -> list[dict]:
    productos = listar_stock()
    q = query.lower()
    return [p for p in productos
            if q in p.get("codigo", "").lower()
            or q in p.get("descripcion", "").lower()]


# ── Actualizar fórmulas planilla existente ────────────────────────────────────

def actualizar_formulas_planilla() -> str:
    """
    Aplica las fórmulas de vinculación a una planilla ya existente.
    Crea la hoja Stock si no existe. Conecta: Libro Contable ↔ Cashflow ↔ Stock.
    """
    sid = get_spreadsheet_id()
    svc = _sheets()

    # Crear hoja Stock si no existe
    meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
    existing = {s["properties"]["title"] for s in meta["sheets"]}
    if "Stock" not in existing:
        svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": [
            {"addSheet": {"properties": {
                "title": "Stock",
                "tabColor": {"red": 0.60, "green": 0.20, "blue": 0.80},
            }}}
        ]}).execute()
        _setup_stock(svc, sid)

    updates = [
        ("Libro Contable!C5", [["=Cashflow!C5"]]),
        ("Libro Contable!C6", [["=SUM(Cashflow!C6:C9)"]]),
        ("Libro Contable!C8", [["=SUMPRODUCT(IFERROR(Stock!B2:B1000,0),IFERROR(Stock!C2:C1000,0))"]]),
        ("Libro Contable!C10", [["=SUM(C5:C9)"]]),
        ("Libro Contable!C17", [["=SUM(C14:C16)"]]),
        ("Libro Contable!C19", [["=C10-C17"]]),
        ("Cashflow!C10",       [["=SUM(C5:C9)"]]),
    ]

    for rng, values in updates:
        try:
            svc.spreadsheets().values().update(
                spreadsheetId=sid, range=rng,
                valueInputOption="USER_ENTERED",
                body={"values": values},
            ).execute()
        except Exception as e:
            return f"Error actualizando {rng}: {e}"

    return (
        "Fórmulas aplicadas:\n"
        "• Libro Contable C5 = Cashflow!C5 (Efectivo en caja)\n"
        "• Libro Contable C6 = SUM(Cashflow!C6:C9) (Cuentas bancarias)\n"
        "• Libro Contable C8 = Stock (valor inventario)\n"
        "• Totales y patrimonio neto recalculados\n"
        "• Cashflow total liquidez recalculado"
    )


# ── Info general ──────────────────────────────────────────────────────────────

def get_spreadsheet_url() -> str:
    return f"https://docs.google.com/spreadsheets/d/{get_spreadsheet_id()}"


# ══════════════════════════════════════════════════════════════════════════════
# NUEVA ESTRUCTURA: hoja "Finanzas" (fusión de Libro Contable + Cashflow)
# ══════════════════════════════════════════════════════════════════════════════

def _hoja_finanzas_existe() -> bool:
    sid = get_spreadsheet_id()
    meta = _sheets().spreadsheets().get(spreadsheetId=sid).execute()
    return any(s["properties"]["title"] == "Finanzas" for s in meta["sheets"])


def registrar_movimiento_finanzas(descripcion: str, ingreso: float = 0,
                                    egreso: float = 0, categoria: str = "General",
                                    cuenta: str = "Efectivo en caja",
                                    fecha: str = "") -> str:
    """
    Registra un movimiento en la hoja Finanzas (estructura nueva unificada).
    Si la hoja no existe aún, cae back al sistema anterior.
    """
    if not _hoja_finanzas_existe():
        # Fallback al sistema anterior mientras se migra
        if ingreso:
            r1 = registrar_movimiento(descripcion=descripcion, haber=ingreso, categoria=categoria, fecha=fecha)
            r2 = registrar_movimiento_cashflow(descripcion=descripcion, ingreso=ingreso, cuenta=cuenta, fecha=fecha)
            return f"{r1} | {r2}"
        else:
            r1 = registrar_movimiento(descripcion=descripcion, debe=egreso, categoria=categoria, fecha=fecha)
            r2 = registrar_movimiento_cashflow(descripcion=descripcion, egreso=egreso, cuenta=cuenta, fecha=fecha)
            return f"{r1} | {r2}"

    sid = get_spreadsheet_id()
    svc = _sheets()
    if not fecha:
        fecha = datetime.now().strftime("%d/%m/%Y")

    # Obtener último N° de movimiento
    res = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Finanzas!A19:H"
    ).execute()
    movs = res.get("values", [])
    n = len(movs) + 1

    row = [[fecha, n, descripcion,
            ingreso if ingreso else "",
            egreso  if egreso  else "",
            categoria, cuenta, ""]]  # saldo: fórmula dinámica

    svc.spreadsheets().values().append(
        spreadsheetId=sid, range="Finanzas!A:H",
        valueInputOption="USER_ENTERED",
        body={"values": row},
    ).execute()

    # Escribir fórmula de saldo acumulado en la fila recién agregada
    fila_nueva = 18 + n
    if n == 1:
        formula_saldo = f"=D{fila_nueva}-E{fila_nueva}"
    else:
        formula_saldo = f"=H{fila_nueva - 1}+D{fila_nueva}-E{fila_nueva}"

    svc.spreadsheets().values().update(
        spreadsheetId=sid, range=f"Finanzas!H{fila_nueva}",
        valueInputOption="USER_ENTERED",
        body={"values": [[formula_saldo]]},
    ).execute()

    tipo = "Ingreso" if ingreso else "Egreso"
    monto = ingreso or egreso
    return (f"✓ {tipo} registrado en Finanzas: {descripcion} — "
            f"${monto:,.0f} | Categoría: {categoria} | Cuenta: {cuenta}")


def obtener_resumen_finanzas() -> dict:
    """
    Lee los KPIs calculados por fórmulas en la sección POSICIÓN ACTUAL (C4:C7).
    Funciona con la nueva hoja Finanzas.
    """
    if not _hoja_finanzas_existe():
        return obtener_resumen_contable()   # fallback

    sid = get_spreadsheet_id()
    res = _sheets().spreadsheets().values().get(
        spreadsheetId=sid, range="Finanzas!A4:C15"
    ).execute()
    rows = res.get("values", [])

    def val(r, c=2):
        try:
            return float(str(rows[r][c]).replace(",", ".").replace("$", "").replace(".", "").strip() or "0")
        except:
            return 0.0

    return {
        "ingresos_mes":    val(0),   # C4
        "egresos_mes":     val(1),   # C5
        "resultado_neto":  val(2),   # C6
        "total_liquidez":  val(3),   # C7
        "cuentas": {
            "efectivo":          val(6),   # C10
            "banco_cte":         val(7),   # C11
            "banco_ahorro":      val(8),   # C12
            "mercado_pago":      val(9),   # C13
            "otros":             val(10),  # C14
        }
    }


def listar_movimientos_finanzas(limit: int = 50) -> list[dict]:
    """Devuelve los últimos N movimientos de la hoja Finanzas."""
    if not _hoja_finanzas_existe():
        return []
    sid = get_spreadsheet_id()
    res = _sheets().spreadsheets().values().get(
        spreadsheetId=sid, range="Finanzas!A19:H"
    ).execute()
    rows = res.get("values", [])
    keys = ["fecha", "numero", "descripcion", "ingreso", "egreso", "categoria", "cuenta", "saldo"]
    movs = [dict(zip(keys, row + [""] * (len(keys) - len(row)))) for row in rows if any(row)]
    return list(reversed(movs))[:limit]   # más recientes primero


def get_dashboard_data() -> dict:
    """
    Datos completos para el dashboard de la plataforma.
    Devuelve KPIs financieros + stock bajo + últimos movimientos.
    """
    finanzas = obtener_resumen_finanzas()
    movimientos = listar_movimientos_finanzas(limit=10)

    # Stock bajo (bajo mínimo o ≤5 si no tiene mínimo configurado)
    try:
        stock = listar_stock()
        stock_bajo = []
        for p in stock:
            unidades    = int(str(p.get("unidades", "0")).strip() or "0")
            stock_min   = int(str(p.get("stock_minimo", "5")).strip() or "5")
            if unidades <= stock_min and p.get("codigo", "").strip():
                stock_bajo.append({
                    "codigo":      p.get("codigo", ""),
                    "descripcion": p.get("descripcion", ""),
                    "unidades":    unidades,
                    "stock_minimo": stock_min,
                })
    except Exception:
        stock_bajo = []

    return {
        "finanzas":     finanzas,
        "movimientos":  movimientos,
        "stock_bajo":   stock_bajo,
        "generado_el":  datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


# ── Clientes CRM (campos extendidos) ─────────────────────────────────────────

def actualizar_cliente_crm(client_id: str, ultima_visita: str = "",
                             proximo_seguimiento: str = "",
                             estado: str = "", tags: str = "") -> str:
    """Actualiza los campos CRM de un cliente existente (columnas H-L)."""
    sid = get_spreadsheet_id()
    svc = _sheets()
    res = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Clientes!A2:L"
    ).execute()
    rows = res.get("values", [])
    for i, row in enumerate(rows):
        if row and str(row[0]) == str(client_id):
            fila = i + 2
            updates = {}
            if estado:            updates[f"Clientes!H{fila}"] = estado
            if ultima_visita:     updates[f"Clientes!J{fila}"] = ultima_visita
            if proximo_seguimiento: updates[f"Clientes!K{fila}"] = proximo_seguimiento
            if tags:              updates[f"Clientes!L{fila}"] = tags
            for rng, val in updates.items():
                svc.spreadsheets().values().update(
                    spreadsheetId=sid, range=rng,
                    valueInputOption="USER_ENTERED",
                    body={"values": [[val]]},
                ).execute()
            nombre = f"{row[1]} {row[2]}".strip() if len(row) > 2 else f"ID#{client_id}"
            return f"Cliente '{nombre}' actualizado: {', '.join(f'{k}={v}' for k,v in {'estado':estado,'ultima_visita':ultima_visita,'seguimiento':proximo_seguimiento,'tags':tags}.items() if v)}"
    return f"Cliente con ID '{client_id}' no encontrado."


