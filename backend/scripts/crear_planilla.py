"""
Script de setup inicial — crea la Planilla Maestra en Google Drive.

Uso:
    cd backend
    python scripts/crear_planilla.py --nombre "Mi Negocio"

Requisitos previos:
    1. Tener un archivo credentials.json (service account de Google Cloud)
    2. Habilitar las APIs: Google Sheets API y Google Drive API
    3. GOOGLE_DRIVE_CREDENTIALS_PATH en .env apuntando al credentials.json

Al finalizar imprime la URL de la planilla y guarda el ID en pokeoffice.config.json.
"""
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.sheets_client import crear_planilla_maestra, get_spreadsheet_url, save_config


def main():
    parser = argparse.ArgumentParser(description="Crear Planilla Maestra de Pokeoffice")
    parser.add_argument("--nombre", required=True, help='Nombre del negocio (ej: "Ferretería López")')
    args = parser.parse_args()

    print(f"\n[*] Creando Planilla Maestra para: {args.nombre}")
    print("    Conectando con Google Sheets...\n")

    try:
        sid = crear_planilla_maestra(args.nombre)
        url = f"https://docs.google.com/spreadsheets/d/{sid}"

        print("[OK] Planilla creada exitosamente!\n")
        print(f"    URL: {url}")
        print(f"    ID:  {sid}\n")
        print("    Hojas creadas:")
        print("      - Clientes       -- CRM basico")
        print("      - Libro Contable -- Activos / Pasivos / Movimientos")
        print("      - Cashflow       -- Posiciones bancarias / Flujo de caja\n")
        print("    El ID fue guardado en pokeoffice.config.json.")
        print("    Los agentes ya pueden usar la planilla.\n")
        print("    IMPORTANTE: compartí la planilla con tu cuenta de Google")
        print("    para poder editarla manualmente también.")
        print(f"    Andá a: {url}\n")

    except FileNotFoundError:
        print("[ERROR] No se encontró el archivo credentials.json")
        print("    Seguí estos pasos:")
        print("    1. Entrá a https://console.cloud.google.com")
        print("    2. Creá un proyecto → APIs → habilitá Google Sheets API y Google Drive API")
        print("    3. IAM → Cuentas de servicio → Crear → Descargar JSON")
        print("    4. Renombrá el archivo a credentials.json")
        print("    5. Ponelo en la carpeta backend/")
        print("    6. Actualizá GOOGLE_DRIVE_CREDENTIALS_PATH en .env\n")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
