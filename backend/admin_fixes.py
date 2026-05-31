"""
Fixes ejecutables desde el panel admin.
Cada fix corre para TODOS los tenants activos — nunca para uno solo.
Invariante: agregar aquí solo operaciones idempotentes y seguras.
"""
import logging

log = logging.getLogger("pokeoffice.admin_fixes")


# ── Funciones de fix (síncronas, una por tenant) ──────────────────────────────

def _fix_verificar_planillas(tenant: dict) -> str:
    sid = (tenant.get("spreadsheet_id") or "").strip()
    if not sid:
        return "Sin planilla configurada — omitido"
    from mcp.sheets_client import _sheets
    svc = _sheets()
    meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
    hojas = [s["properties"]["title"] for s in meta["sheets"]]
    return f"OK — hojas: {', '.join(hojas)}"


def _fix_actualizar_formulas(tenant: dict) -> str:
    sid = (tenant.get("spreadsheet_id") or "").strip()
    if not sid:
        return "Sin planilla configurada — omitido"
    from mcp.sheets_client import set_tenant_spreadsheet_id_ctx, actualizar_formulas_planilla
    set_tenant_spreadsheet_id_ctx(sid)
    return actualizar_formulas_planilla()


def _fix_init_estructura(tenant: dict) -> str:
    """Re-inicializa la estructura de hojas (headers) para tenants con planilla desactualizada."""
    sid = (tenant.get("spreadsheet_id") or "").strip()
    if not sid:
        return "Sin planilla configurada — omitido"
    from mcp.sheets_client import set_tenant_spreadsheet_id_ctx, configurar_planilla_existente
    nombre = tenant.get("nombre_negocio") or "Mi Negocio"
    set_tenant_spreadsheet_id_ctx(sid)
    configurar_planilla_existente(sid, nombre)
    return f"Estructura re-inicializada para '{nombre}'"


# ── Registro de fixes disponibles ─────────────────────────────────────────────

FIXES: dict[str, dict] = {
    "verificar_planillas": {
        "nombre":     "Verificar acceso a planillas",
        "descripcion": "Comprueba que la service account puede leer la planilla de cada tenant.",
        "funcion":    _fix_verificar_planillas,
    },
    "actualizar_formulas": {
        "nombre":     "Actualizar fórmulas de planillas",
        "descripcion": "Aplica la estructura de fórmulas actualizada (Finanzas, Stock) a todas las planillas.",
        "funcion":    _fix_actualizar_formulas,
    },
    "init_estructura": {
        "nombre":     "Re-inicializar estructura de hojas",
        "descripcion": "Re-crea headers y estructura de hojas Clientes/Finanzas/Stock para todos los tenants.",
        "funcion":    _fix_init_estructura,
    },
}


# ── Runner principal ───────────────────────────────────────────────────────────

async def run_fix(fix_id: str) -> dict:
    """Ejecuta un fix pre-definido para todos los tenants activos."""
    import asyncio

    fix = FIXES.get(fix_id)
    if not fix:
        return {
            "error": f"Fix '{fix_id}' no registrado.",
            "disponibles": list(FIXES.keys()),
        }

    from db.admin_models import listar_tenants, get_tenant
    tenants = await listar_tenants()

    resultados = []
    for t in tenants:
        if not t.get("activo", 1):
            continue
        # listar_tenants no incluye spreadsheet_id — cargar con get_tenant (SELECT *)
        full = await get_tenant(t["id"])
        if not full:
            continue
        nombre = full.get("nombre_negocio") or full.get("email") or t["id"]
        try:
            # Ejecutar en thread pool para no bloquear el event loop con I/O síncrono de Sheets
            resultado = await asyncio.to_thread(fix["funcion"], full)
            resultados.append({"tenant": nombre, "status": "ok", "resultado": resultado})
            log.info("fix %s — %s: OK", fix_id, nombre)
        except Exception as e:
            resultados.append({"tenant": nombre, "status": "error", "error": str(e)})
            log.error("fix %s — %s: %s", fix_id, nombre, e)

    return {
        "fix_id":              fix_id,
        "nombre":              fix["nombre"],
        "tenants_procesados":  len(resultados),
        "resultados":          resultados,
    }
