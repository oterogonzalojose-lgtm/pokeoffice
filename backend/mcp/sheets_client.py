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
import logging
import contextvars
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("pokeoffice")

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_DATA_DIR    = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent)))
_CONFIG_PATH = _DATA_DIR / "pokeoffice.config.json"

# ContextVar para pasar el spreadsheet_id del tenant activo a través del call stack
# Se setea en run_vp() al inicio de cada request, antes de delegar a agentes.
_tenant_sid_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "tenant_spreadsheet_id", default=""
)

# ContextVar para pasar el tenant_id activo (usado por escalar_problema y otros agentes)
_tenant_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "tenant_id", default=""
)


def set_tenant_spreadsheet_id_ctx(sid: str):
    """Llamar al inicio de cada request con el spreadsheet_id del tenant."""
    _tenant_sid_ctx.set(sid)


def set_tenant_id_ctx(tid: str):
    """Llamar al inicio de cada request con el tenant_id activo."""
    _tenant_id_ctx.set(tid)


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
    # 1. ContextVar seteado por run_vp() al inicio del request (prioridad máxima)
    ctx = _tenant_sid_ctx.get()
    if ctx:
        return ctx
    # 2. Config file local o variable de entorno (fallback / legacy single-tenant)
    sid = load_config().get("spreadsheet_id") or os.getenv("SPREADSHEET_ID", "")
    if not sid:
        raise RuntimeError(
            "Planilla maestra no configurada para este tenant. "
            "Vinculá una Google Sheet desde el panel de configuración."
        )
    return sid


# ── Sheet creation ─────────────────────────────────────────────────────────────

def configurar_planilla_existente(sid: str, nombre_negocio: str = "Mi Negocio") -> str:
    """
    Configura un Google Sheet existente (ya compartido con la cuenta de servicio).
    Estructura actual: Clientes | Finanzas | Stock
    Las hojas "Libro Contable" y "Cashflow" están deprecadas y se eliminan si existen.
    """
    svc = _sheets()

    meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
    existing = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
    default_sheet_id = list(existing.values())[0]
    default_sheet_title = list(existing.keys())[0]

    requests = []

    # Renombrar la primera hoja a "Clientes" si es necesario
    if default_sheet_title not in ("Clientes", "Finanzas", "Stock"):
        requests.append({"updateSheetProperties": {
            "properties": {"sheetId": default_sheet_id, "title": "Clientes",
                           "tabColor": {"red": 0.18, "green": 0.68, "blue": 0.38}},
            "fields": "title,tabColor",
        }})

    # Agregar hojas faltantes (estructura actual)
    for title, color in [
        ("Finanzas", {"red": 0.95, "green": 0.61, "blue": 0.07}),
        ("Stock",    {"red": 0.60, "green": 0.20, "blue": 0.80}),
    ]:
        if title not in existing:
            requests.append({"addSheet": {"properties": {
                "title": title, "tabColor": color,
            }}})

    # Eliminar hojas deprecadas si existen
    for deprecated in ("Libro Contable", "Cashflow"):
        if deprecated in existing:
            requests.append({"deleteSheet": {"sheetId": existing[deprecated]}})

    if requests:
        svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": requests}).execute()

    _setup_clientes(svc, sid)
    _setup_finanzas(svc, sid)
    _setup_stock(svc, sid)
    _apply_formats(svc, sid)

    save_config({"spreadsheet_id": sid, "business_name": nombre_negocio})
    return sid


def crear_planilla_maestra(nombre_negocio: str, email_cliente: Optional[str] = None) -> str:
    """
    Crea la planilla maestra con las 4 hojas preconfiguradas.
    Si se provee email_cliente, transfiere el ownership al cliente y elimina
    el permiso público — la service account mantiene acceso programático como writer.
    Devuelve el spreadsheet_id.
    """
    svc = _sheets()
    drv = _drive()

    # Crear el archivo via Drive API (evita el 403 de Sheets API en proyectos sin Workspace)
    drive_file = drv.files().create(
        body={
            "name": f"{nombre_negocio} — Planilla Maestra Pokeoffice",
            "mimeType": "application/vnd.google-apps.spreadsheet",
        },
        fields="id",
    ).execute()
    sid = drive_file["id"]

    _setup_clientes(svc, sid)
    _setup_cashflow(svc, sid)
    _setup_libro_contable(svc, sid)
    _setup_stock(svc, sid)
    _apply_formats(svc, sid)

    if email_cliente:
        try:
            # Intentar transferir ownership al cliente (requiere cuenta Google asociada al email).
            # Gmail siempre funciona. Hotmail/Outlook solo si el usuario tiene cuenta Google vinculada.
            drv.permissions().create(
                fileId=sid,
                body={"type": "user", "role": "owner", "emailAddress": email_cliente},
                transferOwnership=True,
            ).execute()
            # Sin permiso público — solo el cliente (owner) y la service account (writer)
        except Exception:
            # Fallback: el email no tiene cuenta Google asociada.
            # Compartir como writer para que igual pueda acceder con el link.
            log.warning("No se pudo transferir ownership a %s — compartiendo como writer", email_cliente)
            drv.permissions().create(
                fileId=sid,
                body={"type": "user", "role": "writer", "emailAddress": email_cliente},
            ).execute()
    else:
        # Sin email de cliente: acceso público con link como fallback de desarrollo
        drv.permissions().create(
            fileId=sid,
            body={"type": "anyone", "role": "writer"},
        ).execute()

    save_config({"spreadsheet_id": sid, "business_name": nombre_negocio})
    return sid


def _setup_clientes(svc, sid: str):
    headers = [["#", "Nombre", "Apellido", "Teléfono", "Email", "Comentarios", "Fecha de Alta"]]
    _write(svc, sid, "Clientes!A1:G1", headers)


def _setup_finanzas(svc, sid: str):
    """Estructura unificada de la hoja Finanzas (reemplaza Libro Contable + Cashflow)."""
    rows = [
        ["FINANZAS — Libro Contable Unificado"],
        [],
        ["— RESUMEN DEL MES —"],
        ["Ingresos del mes ($)",  "", "=SUMIF(F19:F,\"Ingreso\",D19:D)"],
        ["Egresos del mes ($)",   "", "=SUMIF(F19:F,\"Egreso\",E19:E)"],
        ["Resultado neto ($)",    "", "=C4-C5"],
        ["Total liquidez ($)",    "", "=SUM(C10:C14)"],
        [],
        ["— POSICIÓN POR CUENTA —"],
        ["Efectivo en caja",           "", 0],
        ["Banco cte.",                 "", 0],
        ["Banco (cja. ahorro)",        "", 0],
        ["Mercado Pago",               "", 0],
        ["Otros",                      "", 0],
        ["TOTAL LIQUIDEZ",             "", "=SUM(C10:C14)"],
        [],
        [],
        ["— MOVIMIENTOS —"],
        ["Fecha", "N°", "Descripción", "Ingreso ($)", "Egreso ($)", "Categoría", "Cuenta", "Saldo acumulado"],
    ]
    _write(svc, sid, "Finanzas!A1:H19", rows)


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
    headers = [["Código", "Unidades", "Precio ($)", "Promoción", "Descripción",
                "Última act.", "Stock mínimo", "Costo compra ($)", "Proveedor", "Margen ($)"]]
    _write(svc, sid, "Stock!A1:J1", headers)


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
        ("Clientes", 0, {"red": 0.18, "green": 0.68, "blue": 0.38}),
        ("Finanzas", 0, {"red": 0.95, "green": 0.61, "blue": 0.07}),
        ("Stock",    0, {"red": 0.60, "green": 0.20, "blue": 0.80}),
    ]:
        if title not in sheet_ids:
            continue
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_ids[title], "startRowIndex": row, "endRowIndex": row+1},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": color,
                    "textFormat": {"bold": True, "fontSize": 12},
                }},
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        })

    if requests:
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


def registrar_entrada_stock(codigo: str, descripcion: str, unidades: int,
                             precio_venta: float = 0.0, costo_compra: float = 0.0,
                             proveedor: str = "", stock_minimo: int = 5) -> str:
    """
    Registra entrada de mercadería al stock.
    Si el producto ya existe (por código), suma las unidades y actualiza datos.
    Si no existe, crea una nueva fila con todos los campos.
    """
    sid = get_spreadsheet_id()
    svc = _sheets()
    fecha = datetime.now().strftime("%d/%m/%Y")
    margen = round(precio_venta - costo_compra, 2) if precio_venta and costo_compra else ""

    result = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Stock!A2:J"
    ).execute()
    rows = result.get("values", [])

    for i, row in enumerate(rows):
        if row and str(row[0]).strip().lower() == codigo.strip().lower():
            try:
                actuales = int(str(row[1]).strip() or "0")
            except ValueError:
                actuales = 0
            nuevas = actuales + unidades
            row_num = i + 2
            svc.spreadsheets().values().update(
                spreadsheetId=sid,
                range=f"Stock!A{row_num}:J{row_num}",
                valueInputOption="USER_ENTERED",
                body={"values": [[
                    codigo, nuevas, precio_venta or (row[2] if len(row) > 2 else ""),
                    row[3] if len(row) > 3 else "",
                    descripcion or (row[4] if len(row) > 4 else ""),
                    fecha,
                    stock_minimo or (row[6] if len(row) > 6 else 5),
                    costo_compra or (row[7] if len(row) > 7 else ""),
                    proveedor or (row[8] if len(row) > 8 else ""),
                    margen,
                ]]},
            ).execute()
            return (f"✓ Stock actualizado: '{descripcion or codigo}' — "
                    f"{actuales} → {nuevas} unidades | Precio: ${precio_venta:,.0f} | "
                    f"Costo: ${costo_compra:,.0f}")

    # Producto nuevo
    new_row = [[codigo, unidades, precio_venta, "", descripcion, fecha,
                stock_minimo, costo_compra, proveedor, margen]]
    svc.spreadsheets().values().append(
        spreadsheetId=sid, range="Stock!A:J",
        valueInputOption="USER_ENTERED", body={"values": new_row},
    ).execute()
    return (f"✓ Producto nuevo en stock: '{descripcion}' (código: {codigo}) — "
            f"{unidades} unidades | Precio: ${precio_venta:,.0f} | "
            f"Costo: ${costo_compra:,.0f} | Proveedor: {proveedor or '—'}")


def actualizar_precio_stock(query: str, precio_venta: float = 0.0,
                             costo_compra: float = 0.0) -> str:
    """
    Actualiza el precio de venta (y opcionalmente el costo) de un producto existente.
    Busca por código o descripción (coincidencia parcial). Actualiza la primera coincidencia.
    """
    sid = get_spreadsheet_id()
    svc = _sheets()
    result = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Stock!A2:J"
    ).execute()
    rows = result.get("values", [])
    q = query.lower()
    for i, row in enumerate(rows):
        codigo_row = str(row[0]).strip().lower() if row else ""
        desc_row   = str(row[4]).strip().lower() if len(row) > 4 else ""
        if q in codigo_row or q in desc_row:
            row_num = i + 2
            nuevo_precio = precio_venta if precio_venta else (float(row[2]) if len(row) > 2 and row[2] else 0)
            nuevo_costo  = costo_compra if costo_compra else (float(row[7]) if len(row) > 7 and row[7] else 0)
            margen = round(nuevo_precio - nuevo_costo, 2) if nuevo_precio and nuevo_costo else ""
            fecha  = datetime.now().strftime("%d/%m/%Y")
            svc.spreadsheets().values().update(
                spreadsheetId=sid,
                range=f"Stock!C{row_num}:J{row_num}",
                valueInputOption="USER_ENTERED",
                body={"values": [[
                    nuevo_precio,
                    row[3] if len(row) > 3 else "",
                    row[4] if len(row) > 4 else "",
                    fecha,
                    row[6] if len(row) > 6 else 5,
                    nuevo_costo,
                    row[8] if len(row) > 8 else "",
                    margen,
                ]]},
            ).execute()
            nombre = row[4] if len(row) > 4 else row[0]
            return (f"✓ Precio actualizado: '{nombre}' — "
                    f"Precio de venta: ${nuevo_precio:,.0f}"
                    + (f" | Costo: ${nuevo_costo:,.0f}" if nuevo_costo else ""))
    return f"No se encontró '{query}' en el stock. Verificá el nombre o código del producto."


def buscar_producto(query: str) -> list[dict]:
    """
    Búsqueda fuzzy por palabras individuales.
    'platitos de aluminio' encuentra 'Platito de aluminio' porque 'aluminio' matchea.
    Ignora palabras de ≤2 caracteres (artículos, preposiciones).
    """
    productos = listar_stock()
    words = [w for w in query.lower().split() if len(w) > 2]
    if not words:
        return []

    def matches(p: dict) -> bool:
        text = " ".join([
            p.get("codigo", ""),
            p.get("descripcion", ""),
            p.get("proveedor", ""),
        ]).lower()
        # Coincide si CUALQUIER palabra del query aparece en el texto completo
        return any(w in text for w in words)

    return [p for p in productos if matches(p)]


def _num_to_col_letter(n: int) -> str:
    """Convierte número de columna 1-indexed a letra(s): 1→A, 26→Z, 27→AA."""
    result = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def actualizar_campo_cliente(nombre_cliente: str, campo: str, valor: str) -> str:
    """
    Actualiza un campo específico de un cliente existente.
    Busca el cliente por nombre (fuzzy) y la columna por su header (case-insensitive).
    Funciona con columnas default y columnas personalizadas.
    """
    sid = get_spreadsheet_id()
    svc = _sheets()

    result = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Clientes!A1:ZZ"
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return "No hay datos en la hoja Clientes."

    headers = rows[0]

    # Encontrar la columna por nombre (case-insensitive)
    col_idx = next((i for i, h in enumerate(headers) if h.lower() == campo.lower()), None)
    if col_idx is None:
        return (
            f"No se encontró la columna '{campo}' en Clientes. "
            f"Columnas disponibles: {', '.join(headers)}."
        )

    # Buscar cliente por nombre (fuzzy: cualquier parte del nombre completo)
    q = nombre_cliente.lower().strip()
    for i, row in enumerate(rows[1:], start=2):
        nombre  = str(row[1] if len(row) > 1 else "").lower()
        apellido = str(row[2] if len(row) > 2 else "").lower()
        full    = f"{nombre} {apellido}".strip()
        if q in nombre or q in apellido or q in full:
            col_letter = _num_to_col_letter(col_idx + 1)
            svc.spreadsheets().values().update(
                spreadsheetId=sid,
                range=f"Clientes!{col_letter}{i}",
                valueInputOption="USER_ENTERED",
                body={"values": [[valor]]},
            ).execute()
            nombre_completo = f"{row[1] if len(row) > 1 else ''} {row[2] if len(row) > 2 else ''}".strip()
            return f"✓ '{campo}' de {nombre_completo} actualizado a '{valor}'."

    return f"No se encontró ningún cliente con el nombre '{nombre_cliente}'."


def agregar_columna_personalizada(hoja: str, nombre_columna: str) -> str:
    """
    Agrega una columna al final de la hoja indicada (Clientes o Stock).
    La hoja Finanzas está protegida — no se puede modificar desde aquí.
    """
    HOJAS_PERMITIDAS = {"Clientes", "Stock"}
    if hoja not in HOJAS_PERMITIDAS:
        return (
            f"La hoja '{hoja}' no permite columnas personalizadas. "
            f"Solo se puede modificar: {', '.join(sorted(HOJAS_PERMITIDAS))}. "
            f"La hoja Finanzas solo puede ser modificada por el equipo de Pokeoffice."
        )

    sid = get_spreadsheet_id()
    svc = _sheets()
    result = svc.spreadsheets().values().get(
        spreadsheetId=sid, range=f"{hoja}!1:1"
    ).execute()
    headers = result.get("values", [[]])[0] if result.get("values") else []

    if any(nombre_columna.lower() == h.lower() for h in headers):
        return f"La columna '{nombre_columna}' ya existe en la hoja {hoja}."

    col_letter = _num_to_col_letter(len(headers) + 1)
    svc.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f"{hoja}!{col_letter}1",
        valueInputOption="USER_ENTERED",
        body={"values": [[nombre_columna]]},
    ).execute()
    return f"✓ Columna '{nombre_columna}' agregada en {hoja} (columna {col_letter})."


def registrar_salida_stock(query: str, cantidad: int) -> str:
    """
    Registra la salida de stock por venta. Reduce unidades del producto encontrado (fuzzy).
    No puede dejar stock negativo. Devuelve el precio de venta para que el VP
    lo use al registrar el ingreso en el Contador.
    """
    sid = get_spreadsheet_id()
    svc = _sheets()
    result = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Stock!A2:J"
    ).execute()
    rows = result.get("values", [])
    words = [w for w in query.lower().split() if len(w) > 2]
    if not words:
        return f"Query demasiado corta para buscar '{query}'."

    for i, row in enumerate(rows):
        text = " ".join([
            str(row[0]) if row else "",
            str(row[4]) if len(row) > 4 else "",
        ]).lower()
        if any(w in text for w in words):
            row_num = i + 2
            try:
                actuales = int(str(row[1]).strip() or "0")
            except ValueError:
                actuales = 0
            nuevas = max(0, actuales - cantidad)
            try:
                precio = float(str(row[2]).strip().replace(",", ".") or "0")
            except ValueError:
                precio = 0.0
            fecha = datetime.now().strftime("%d/%m/%Y")
            svc.spreadsheets().values().update(
                spreadsheetId=sid,
                range=f"Stock!B{row_num}:F{row_num}",
                valueInputOption="USER_ENTERED",
                body={"values": [[
                    nuevas,
                    row[2] if len(row) > 2 else "",
                    row[3] if len(row) > 3 else "",
                    row[4] if len(row) > 4 else "",
                    fecha,
                ]]},
            ).execute()
            nombre = row[4] if len(row) > 4 else row[0]
            precio_str = f"${precio:,.0f}" if precio else "precio no registrado en stock"
            return (
                f"✓ Stock bajado por venta: '{nombre}' — "
                f"{actuales} → {nuevas} unidades (-{cantidad} vendidas). "
                f"Precio de venta unitario: {precio_str}."
            )
    return f"No se encontró '{query}' en el stock."


def set_unidades_stock(query: str, cantidad: int) -> str:
    """
    Establece una cantidad EXACTA de unidades para un producto existente.
    No suma — reemplaza. Usar para correcciones de inventario.
    Busca el producto por nombre/código (fuzzy).
    """
    sid = get_spreadsheet_id()
    svc = _sheets()
    result = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Stock!A2:J"
    ).execute()
    rows = result.get("values", [])
    words = [w for w in query.lower().split() if len(w) > 2]

    for i, row in enumerate(rows):
        text = " ".join([
            str(row[0]) if row else "",
            str(row[4]) if len(row) > 4 else "",
        ]).lower()
        if any(w in text for w in words):
            row_num = i + 2
            fecha = datetime.now().strftime("%d/%m/%Y")
            svc.spreadsheets().values().update(
                spreadsheetId=sid,
                range=f"Stock!B{row_num}:F{row_num}",
                valueInputOption="USER_ENTERED",
                body={"values": [[
                    cantidad,
                    row[2] if len(row) > 2 else "",
                    row[3] if len(row) > 3 else "",
                    row[4] if len(row) > 4 else "",
                    fecha,
                ]]},
            ).execute()
            nombre = row[4] if len(row) > 4 else row[0]
            return f"✓ Stock corregido: '{nombre}' — cantidad fijada en {cantidad} unidades."
    return f"No se encontró '{query}' en el stock para corregir."


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

    # Obtener últimos movimientos
    res = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Finanzas!A19:H"
    ).execute()
    movs = res.get("values", [])

    # Dedup: si el último movimiento del día tiene el mismo monto y categoría, rechazar
    if movs:
        last = movs[-1]
        try:
            last_fecha   = str(last[0]) if len(last) > 0 else ""
            last_ingreso = float(str(last[3]).replace(",","").replace("$","").strip() or "0") if len(last) > 3 else 0
            last_egreso  = float(str(last[4]).replace(",","").replace("$","").strip() or "0") if len(last) > 4 else 0
            last_cat     = str(last[5]) if len(last) > 5 else ""
            same_monto   = (last_ingreso == ingreso and ingreso > 0) or (last_egreso == egreso and egreso > 0)
            if same_monto and last_fecha == fecha and last_cat.lower() == categoria.lower():
                monto = ingreso or egreso
                return f"⚠ Movimiento duplicado detectado — ya existe '{str(last[2])}' por ${monto:,.0f} hoy. No se registró de nuevo."
        except Exception:
            pass

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


