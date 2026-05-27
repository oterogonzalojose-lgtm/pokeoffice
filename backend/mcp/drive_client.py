"""
Google Drive client — wrapper básico para operaciones que los agentes necesitan.
Usa service account credentials o OAuth2 según la configuración.
"""
import os
import json
from pathlib import Path
from typing import Optional

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    import io
    DRIVE_AVAILABLE = True
except ImportError:
    DRIVE_AVAILABLE = False

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_service():
    if not DRIVE_AVAILABLE:
        raise RuntimeError("google-api-python-client no está instalado.")

    creds_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "./credentials.json")
    if not Path(creds_path).exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de credenciales en {creds_path}. "
            "Configurá GOOGLE_DRIVE_CREDENTIALS_PATH en .env"
        )

    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def list_files(folder_id: Optional[str] = None, max_results: int = 20) -> list[dict]:
    """Lista archivos en Drive (o en una carpeta específica)."""
    service = _get_service()
    query = f"'{folder_id}' in parents and trashed=false" if folder_id else "trashed=false"
    results = service.files().list(
        q=query,
        pageSize=max_results,
        fields="files(id, name, mimeType, modifiedTime, size)",
    ).execute()
    return results.get("files", [])


def read_file_text(file_id: str) -> str:
    """Lee el contenido de un archivo de texto o Google Doc exportado como texto plano."""
    service = _get_service()
    file_meta = service.files().get(fileId=file_id, fields="mimeType,name").execute()
    mime = file_meta.get("mimeType", "")

    if "google-apps.document" in mime:
        request = service.files().export_media(fileId=file_id, mimeType="text/plain")
    else:
        request = service.files().get_media(fileId=file_id)

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue().decode("utf-8", errors="replace")


def create_doc(title: str, content: str, folder_id: Optional[str] = None) -> str:
    """Crea un Google Doc con el contenido dado. Devuelve el file_id."""
    service = _get_service()
    file_metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document",
    }
    if folder_id:
        file_metadata["parents"] = [folder_id]

    file = service.files().create(body=file_metadata, fields="id").execute()
    file_id = file.get("id")

    # Write content via Docs API (plain text insert)
    docs_service = build("docs", "v1", credentials=_get_service()._http.credentials)
    docs_service.documents().batchUpdate(
        documentId=file_id,
        body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
    ).execute()

    return file_id
