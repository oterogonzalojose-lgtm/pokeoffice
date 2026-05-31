"""
conftest.py — fixtures compartidos para toda la suite de tests de Pokeoffice.

Ejecutar desde la raíz del repo:
    cd pokeoffice && pip install pytest pytest-asyncio && pytest tests/ -v
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Agregar backend al path para poder importar los módulos
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# ── Mocks globales de dependencias externas ───────────────────────────────────
# Se aplican ANTES de cualquier import para evitar que los módulos fallen al cargar.

# Mock de Google APIs (no necesitamos credenciales reales para unit tests)
_mock_google = MagicMock()
sys.modules.setdefault("google", _mock_google)
sys.modules.setdefault("google.oauth2", _mock_google.oauth2)
sys.modules.setdefault("google.oauth2.service_account", _mock_google.oauth2.service_account)
sys.modules.setdefault("googleapiclient", MagicMock())
sys.modules.setdefault("googleapiclient.discovery", MagicMock())

# Mock de Anthropic SDK
_mock_anthropic = MagicMock()
sys.modules.setdefault("anthropic", _mock_anthropic)

# Mock de aiosqlite
_mock_aiosqlite = MagicMock()
sys.modules.setdefault("aiosqlite", _mock_aiosqlite)

# Mock de jwt
_mock_jwt = MagicMock()
sys.modules.setdefault("jwt", _mock_jwt)


# ── Fixtures de Sheets mock ───────────────────────────────────────────────────

@pytest.fixture
def mock_sheets_service():
    """Mock completo del servicio de Google Sheets."""
    svc = MagicMock()
    return svc


@pytest.fixture
def sheets_con_clientes(mock_sheets_service):
    """
    Sheets mock con una hoja Clientes pre-poblada.
    Headers: #, Nombre, Apellido, Teléfono, Email, Comentarios, Fecha de Alta
    """
    clientes_data = [
        ["#", "Nombre", "Apellido", "Teléfono", "Email", "Comentarios", "Fecha de Alta"],
        ["1", "con", "los siguientes datos", "5491160602020", "", "", "31/05/2026"],  # fila corrupta
        ["2", "Fernando", "Barrios",          "5491160602020", "", "", "31/05/2026"],
        ["3", "Daniela",  "Spinelli",          "1155667788",   "", "", "30/05/2026"],
        ["4", "María",    "González",          "1144332211",   "", "", "29/05/2026"],
    ]

    def fake_get(**kwargs):
        rng = kwargs.get("range", "")
        mock_result = MagicMock()
        if "1:1" in rng or "1:ZZ" in rng or "A1:ZZ" in rng:
            mock_result.execute.return_value = {"values": clientes_data}
        elif "A2:G" in rng or "A2:L" in rng:
            mock_result.execute.return_value = {"values": clientes_data[1:]}
        else:
            mock_result.execute.return_value = {"values": clientes_data}
        return mock_result

    mock_sheets_service.spreadsheets.return_value.values.return_value.get.side_effect = fake_get
    mock_sheets_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = {}
    mock_sheets_service.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = {}
    return mock_sheets_service


@pytest.fixture
def sheets_con_stock(mock_sheets_service):
    """Mock con hoja Stock pre-poblada."""
    stock_data = [
        ["Código",       "Unidades", "Precio",  "Promoción", "Descripción",          "Última act.", "Stock mín.", "Costo", "Proveedor", "Margen"],
        ["PLATITO-ALU",  "11",       "2500",    "",          "Platito de aluminio",   "31/05/2026",  "5",          "1500",  "Mayorista", "1000"],
        ["COLLAR-PER",   "5",        "3200",    "",          "Collar para perros",    "31/05/2026",  "3",          "1800",  "PetShop",   "1400"],
        ["CORREA-MED",   "0",        "4500",    "",          "Correa talle mediano",  "31/05/2026",  "2",          "2500",  "PetShop",   "2000"],
        ["SHAMPOO-CAN",  "8",        "1800",    "",          "Shampoo canino 500ml",  "31/05/2026",  "5",          "900",   "Distribuid","900"],
    ]

    def fake_get(**kwargs):
        mock_result = MagicMock()
        mock_result.execute.return_value = {"values": stock_data}
        return mock_result

    mock_sheets_service.spreadsheets.return_value.values.return_value.get.side_effect = fake_get
    mock_sheets_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = {}
    return mock_sheets_service


@pytest.fixture(autouse=True)
def reset_context_var():
    """Resetea el ContextVar de tenant entre tests para evitar contaminación."""
    try:
        from mcp.sheets_client import _tenant_sid_ctx, _tenant_id_ctx
        token1 = _tenant_sid_ctx.set("")
        token2 = _tenant_id_ctx.set("")
        yield
        _tenant_sid_ctx.reset(token1)
        _tenant_id_ctx.reset(token2)
    except Exception:
        yield
