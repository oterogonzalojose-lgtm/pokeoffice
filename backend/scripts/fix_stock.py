"""
Script de reparación: crea la hoja Stock si no existe en la planilla maestra.
Uso: python scripts/fix_stock.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from mcp.sheets_client import _sheets, get_spreadsheet_id, _setup_stock

def main():
    sid = get_spreadsheet_id()
    svc = _sheets()

    print(f"Planilla ID: {sid}")
    print("Verificando hojas existentes...")

    meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
    existing = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
    print(f"Hojas actuales: {list(existing.keys())}")

    if "Stock" in existing:
        print("[OK] La hoja Stock ya existe.")
        # Asegurar que tenga el header
        _setup_stock(svc, sid)
        print("[OK] Header de Stock verificado.")
    else:
        print("[>>] Creando hoja Stock...")
        svc.spreadsheets().batchUpdate(
            spreadsheetId=sid,
            body={"requests": [{"addSheet": {"properties": {
                "title": "Stock",
                "tabColor": {"red": 0.60, "green": 0.20, "blue": 0.80},
            }}}]},
        ).execute()
        _setup_stock(svc, sid)

        # Aplicar formato bold al header de Stock
        meta2 = svc.spreadsheets().get(spreadsheetId=sid).execute()
        stock_id = next(
            s["properties"]["sheetId"]
            for s in meta2["sheets"]
            if s["properties"]["title"] == "Stock"
        )
        svc.spreadsheets().batchUpdate(
            spreadsheetId=sid,
            body={"requests": [{
                "repeatCell": {
                    "range": {"sheetId": stock_id, "startRowIndex": 0, "endRowIndex": 1},
                    "cell": {"userEnteredFormat": {
                        "backgroundColor": {"red": 0.60, "green": 0.20, "blue": 0.80},
                        "textFormat": {"bold": True, "fontSize": 12, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                    }},
                    "fields": "userEnteredFormat(backgroundColor,textFormat)",
                }
            }]},
        ).execute()

        print("[OK] Hoja Stock creada con header.")

    # También aplicar fórmula de inventario en Libro Contable
    if "Libro Contable" in existing:
        print("[>>] Actualizando formula de inventario en Libro Contable C8...")
        svc.spreadsheets().values().update(
            spreadsheetId=sid,
            range="Libro Contable!C8",
            valueInputOption="USER_ENTERED",
            body={"values": [["=SUMPRODUCT(IFERROR(Stock!B2:B1000,0),IFERROR(Stock!C2:C1000,0))"]]},
        ).execute()
        print("[OK] Formula de inventario actualizada.")

    url = f"https://docs.google.com/spreadsheets/d/{sid}"
    print(f"\n[OK] Todo listo. Abri la planilla y deberias ver la pestana Stock:\n  {url}")

if __name__ == "__main__":
    main()
