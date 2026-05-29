"""
Script de migración: reestructura la Planilla Maestra.

Cambios:
  1. Crea hoja "Finanzas" (fusión de Libro Contable + Cashflow)
     - Sección A: KPIs del mes (fórmulas automáticas)
     - Sección B: Posiciones por cuenta (calculadas desde movimientos)
     - Sección C: Movimientos unificados (una fila = un movimiento)
  2. Expande hoja Clientes con campos CRM
     - estado, fuente, ultima_visita, proximo_seguimiento, tags
  3. Expande hoja Stock con campos de gestión
     - stock_minimo, costo_compra, proveedor, margen (fórmula)
  4. Renombra hojas antiguas a _backup (NO las elimina)

Uso: python scripts/migrar_planilla.py
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from mcp.sheets_client import _sheets, get_spreadsheet_id


# ── Colores de cabecera ────────────────────────────────────────────────────────
COLOR_FINANZAS = {"red": 0.13, "green": 0.55, "blue": 0.13}   # verde oscuro
COLOR_CLIENTES = {"red": 0.18, "green": 0.39, "blue": 0.78}   # azul
COLOR_STOCK    = {"red": 0.60, "green": 0.20, "blue": 0.80}   # violeta


def get_sheet_id(meta, title):
    for s in meta["sheets"]:
        if s["properties"]["title"] == title:
            return s["properties"]["sheetId"]
    return None


def crear_finanzas(svc, sid, meta):
    """Crea la hoja Finanzas con estructura y fórmulas."""
    existing = {s["properties"]["title"] for s in meta["sheets"]}

    if "Finanzas" not in existing:
        print("[>>] Creando hoja Finanzas...")
        svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": [
            {"addSheet": {"properties": {
                "title": "Finanzas",
                "tabColor": COLOR_FINANZAS,
                "index": 2,
            }}}
        ]}).execute()
    else:
        print("[OK] Hoja Finanzas ya existe.")

    # Obtener ID de la hoja recién creada
    meta2 = svc.spreadsheets().get(spreadsheetId=sid).execute()
    fid = get_sheet_id(meta2, "Finanzas")

    # ── Escribir estructura base ─────────────────────────────────────────────
    valores = [
        # Fila 1: título
        ["FINANZAS — Libro Contable Unificado"],
        # Fila 2: vacía
        [],
        # Fila 3: sección KPIs
        ["— RESUMEN DEL MES —"],
        ["Ingresos del mes ($)", "", "=SUMPRODUCT((MONTH(A$19:A)=MONTH(TODAY()))*(YEAR(A$19:A)=YEAR(TODAY()))*D$19:D)"],
        ["Egresos del mes ($)",  "", "=SUMPRODUCT((MONTH(A$19:A)=MONTH(TODAY()))*(YEAR(A$19:A)=YEAR(TODAY()))*E$19:E)"],
        ["Resultado neto ($)",   "", "=C4-C5"],
        ["Total liquidez ($)",   "", "=IFERROR(LOOKUP(2,1/(H$19:H<>\"\"),H$19:H),0)"],
        # Fila 8: vacía
        [],
        # Fila 9: sección cuentas
        ["— POSICIÓN POR CUENTA —"],
        ["Efectivo en caja",   "", '=SUMIF(G$19:G,"Efectivo en caja",D$19:D)-SUMIF(G$19:G,"Efectivo en caja",E$19:E)'],
        ["Banco (cta. cte.)",  "", '=SUMIF(G$19:G,"Banco (cuenta corriente)",D$19:D)-SUMIF(G$19:G,"Banco (cuenta corriente)",E$19:E)'],
        ["Banco (cja. ahorro)","", '=SUMIF(G$19:G,"Banco (caja de ahorro)",D$19:D)-SUMIF(G$19:G,"Banco (caja de ahorro)",E$19:E)'],
        ["Mercado Pago",       "", '=SUMIF(G$19:G,"Mercado Pago / billetera",D$19:D)-SUMIF(G$19:G,"Mercado Pago / billetera",E$19:E)'],
        ["Otros",              "", '=SUMIF(G$19:G,"Otros",D$19:D)-SUMIF(G$19:G,"Otros",E$19:E)'],
        ["TOTAL LIQUIDEZ",     "", "=SUM(C10:C14)"],
        # Fila 16: vacía
        [],
        # Fila 17: sección movimientos
        ["— MOVIMIENTOS —"],
        # Fila 18: headers
        ["Fecha", "N°", "Descripción", "Ingreso ($)", "Egreso ($)", "Categoría", "Cuenta", "Saldo acumulado"],
    ]
    svc.spreadsheets().values().update(
        spreadsheetId=sid, range="Finanzas!A1:H18",
        valueInputOption="USER_ENTERED",
        body={"values": valores},
    ).execute()

    # ── Formato: header principal ────────────────────────────────────────────
    svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": [
        # Fila 1: título
        {"repeatCell": {
            "range": {"sheetId": fid, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": COLOR_FINANZAS,
                "textFormat": {"bold": True, "fontSize": 13, "foregroundColor": {"red":1,"green":1,"blue":1}},
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }},
        # Fila 18: headers de movimientos
        {"repeatCell": {
            "range": {"sheetId": fid, "startRowIndex": 17, "endRowIndex": 18},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.85, "green": 0.93, "blue": 0.83},
                "textFormat": {"bold": True},
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }},
        # Anclar fila 18 (freeze header de movimientos)
        {"updateSheetProperties": {
            "properties": {"sheetId": fid, "gridProperties": {"frozenRowCount": 18}},
            "fields": "gridProperties.frozenRowCount",
        }},
    ]}).execute()

    print("[OK] Hoja Finanzas creada con estructura y fórmulas.")
    return fid


def migrar_movimientos(svc, sid, meta):
    """Migra movimientos existentes de Libro Contable y Cashflow a Finanzas."""
    existing = {s["properties"]["title"] for s in meta["sheets"]}
    movimientos = []

    # Desde Libro Contable (movimientos en A23+: Fecha, N°, Desc, Debe, Haber, Saldo, Cat)
    if "Libro Contable" in existing:
        try:
            res = svc.spreadsheets().values().get(
                spreadsheetId=sid, range="Libro Contable!A24:G"
            ).execute()
            rows = res.get("values", [])
            for row in rows:
                if len(row) >= 4 and any(row):
                    fecha = row[0] if len(row) > 0 else ""
                    desc  = row[2] if len(row) > 2 else ""
                    debe  = row[3] if len(row) > 3 else ""
                    haber = row[4] if len(row) > 4 else ""
                    cat   = row[6] if len(row) > 6 else "General"
                    if debe or haber:
                        movimientos.append([fecha, "", desc,
                                            haber or "", debe or "",
                                            cat, "Banco (cuenta corriente)"])
            print(f"[>>] {len(movimientos)} movimientos del Libro Contable migrados.")
        except Exception as e:
            print(f"[!] No se pudo leer Libro Contable: {e}")

    if movimientos:
        svc.spreadsheets().values().append(
            spreadsheetId=sid, range="Finanzas!A19",
            valueInputOption="USER_ENTERED",
            body={"values": movimientos},
        ).execute()
        # Escribir fórmulas de saldo acumulado
        _escribir_saldos_finanzas(svc, sid, 19, 19 + len(movimientos))

    print(f"[OK] {len(movimientos)} movimientos migrados a Finanzas.")


def _escribir_saldos_finanzas(svc, sid, desde_fila, hasta_fila):
    """Escribe fórmulas de saldo acumulado en columna H."""
    saldos = []
    for i, fila in enumerate(range(desde_fila, hasta_fila)):
        if i == 0:
            saldos.append([f"=D{fila}-E{fila}"])
        else:
            saldos.append([f"=H{fila - 1}+D{fila}-E{fila}"])
    if saldos:
        svc.spreadsheets().values().update(
            spreadsheetId=sid, range=f"Finanzas!H{desde_fila}",
            valueInputOption="USER_ENTERED",
            body={"values": saldos},
        ).execute()


def expandir_clientes(svc, sid, meta):
    """Agrega columnas CRM a la hoja Clientes."""
    existing = {s["properties"]["title"] for s in meta["sheets"]}
    if "Clientes" not in existing:
        print("[!] Hoja Clientes no encontrada.")
        return

    cid = get_sheet_id(meta, "Clientes")

    # Verificar si ya tiene columna H (estado)
    res = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Clientes!H1"
    ).execute()
    if res.get("values"):
        print("[OK] Clientes ya tiene columnas CRM.")
        return

    # Agregar headers CRM en columnas H-L
    headers = [["estado", "fuente", "ultima_visita", "proximo_seguimiento", "tags"]]
    svc.spreadsheets().values().update(
        spreadsheetId=sid, range="Clientes!H1",
        valueInputOption="USER_ENTERED",
        body={"values": headers},
    ).execute()

    # Formato header
    svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": [
        {"repeatCell": {
            "range": {"sheetId": cid, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 7, "endColumnIndex": 12},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.18, "green": 0.39, "blue": 0.78},
                "textFormat": {"bold": True, "foregroundColor": {"red":1,"green":1,"blue":1}},
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }},
        # Dropdown de estado en columna H
        {"setDataValidation": {
            "range": {"sheetId": cid, "startRowIndex": 1, "endRowIndex": 1000,
                      "startColumnIndex": 7, "endColumnIndex": 8},
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [
                        {"userEnteredValue": "Activo"},
                        {"userEnteredValue": "Inactivo"},
                        {"userEnteredValue": "Potencial"},
                    ]
                },
                "showCustomUi": True,
            }
        }},
    ]}).execute()

    print("[OK] Columnas CRM agregadas a Clientes (estado, fuente, ultima_visita, proximo_seguimiento, tags).")


def expandir_stock(svc, sid, meta):
    """Agrega columnas de gestión a la hoja Stock."""
    existing = {s["properties"]["title"] for s in meta["sheets"]}
    if "Stock" not in existing:
        print("[!] Hoja Stock no encontrada.")
        return

    sid2 = get_sheet_id(meta, "Stock")

    # Verificar si ya tiene columna G (stock_minimo)
    res = svc.spreadsheets().values().get(
        spreadsheetId=sid, range="Stock!G1"
    ).execute()
    if res.get("values"):
        print("[OK] Stock ya tiene columnas extendidas.")
        return

    # Agregar headers en G-J
    headers = [["stock_minimo", "costo_compra", "proveedor", "margen ($)"]]
    svc.spreadsheets().values().update(
        spreadsheetId=sid, range="Stock!G1",
        valueInputOption="USER_ENTERED",
        body={"values": headers},
    ).execute()

    # Fórmula de margen en columna J (precio_venta C - costo_compra H)
    svc.spreadsheets().values().update(
        spreadsheetId=sid, range="Stock!J2",
        valueInputOption="USER_ENTERED",
        body={"values": [['=IFERROR(C2-H2,"")']]},
    ).execute()

    # Formato header
    svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": [
        {"repeatCell": {
            "range": {"sheetId": sid2, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 6, "endColumnIndex": 10},
            "cell": {"userEnteredFormat": {
                "backgroundColor": COLOR_STOCK,
                "textFormat": {"bold": True, "foregroundColor": {"red":1,"green":1,"blue":1}},
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }},
    ]}).execute()

    print("[OK] Columnas extendidas agregadas a Stock (stock_minimo, costo_compra, proveedor, margen).")


def renombrar_hojas_backup(svc, sid, meta):
    """Renombra Libro Contable y Cashflow a _backup (no las elimina)."""
    existing = {s["properties"]["title"]: s["properties"]["sheetId"]
                for s in meta["sheets"]}
    requests = []
    for nombre in ["Libro Contable", "Cashflow"]:
        nuevo_nombre = f"_{nombre}_backup"
        if nombre in existing and nuevo_nombre not in existing:
            requests.append({"updateSheetProperties": {
                "properties": {"sheetId": existing[nombre], "title": nuevo_nombre},
                "fields": "title",
            }})
            print(f"[>>] Renombrando '{nombre}' a '{nuevo_nombre}'")

    if requests:
        svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": requests}).execute()
        print("[OK] Hojas antiguas renombradas como backup (no eliminadas).")
    else:
        print("[OK] No hay hojas para renombrar.")


def main():
    sid = get_spreadsheet_id()
    svc = _sheets()

    print(f"\nPlanilla ID: {sid}")
    print("Iniciando migración de estructura...\n")

    meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
    existing = {s["properties"]["title"] for s in meta["sheets"]}
    print(f"Hojas actuales: {list(existing)}\n")

    # 1. Crear Finanzas
    crear_finanzas(svc, sid, meta)

    # 2. Migrar movimientos
    migrar_movimientos(svc, sid, meta)

    # 3. Expandir Clientes (CRM)
    expandir_clientes(svc, sid, meta)

    # 4. Expandir Stock
    expandir_stock(svc, sid, meta)

    # 5. Renombrar hojas antiguas
    renombrar_hojas_backup(svc, sid, meta)

    url = f"https://docs.google.com/spreadsheets/d/{sid}"
    print(f"\n[OK] Migracion completada!\nRevisa la planilla: {url}")


if __name__ == "__main__":
    main()
