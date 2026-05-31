"""
completar_seed.py — Completa el seed usando los tenants ya creados.

Uso:
    python completar_seed.py

Registra usuarios, vincula planillas y popula datos.
Requiere que seed_tenants.py haya corrido primero (tenants ya creados).
"""
import asyncio
import os
import json
from pathlib import Path
import httpx

API_URL    = os.getenv("POKEOFFICE_URL", "https://pokeoffice-production.up.railway.app")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "")
TIMEOUT    = 90.0
HERE       = Path(__file__).parent

# ── Tenants creados en el primer run ─────────────────────────────────────────
TENANTS = [
    {
        "negocio": "Valentina Masajes",
        "tenant_id": "6357146a-fc2d-4828-9c58-c8f4f683a384",
        "email": "valentina.masajes.test@pokeoffice.ar",
        "codigo": "847360",
        "spreadsheet_id": "",  # Completar con el ID de la hoja después de crearla
    },
    {
        "negocio": "Tornería Villanueva",
        "tenant_id": "81a68fe8-1359-40cc-9673-cdb82e121e83",
        "email": "hector.tornero.test@pokeoffice.ar",
        "codigo": "437400",
        "spreadsheet_id": "",
    },
    {
        "negocio": "Taller Quiroga Chapa y Pintura",
        "tenant_id": "ec02a35a-6195-4607-aeb2-f614d2762399",
        "email": "taller.quiroga.test@pokeoffice.ar",
        "codigo": "114833",
        "spreadsheet_id": "",
    },
    {
        "negocio": "Sofía Mates & Arte",
        "tenant_id": "cea0fac7-9af6-4e96-931d-27e2d12c8907",
        "email": "sofia.mates.test@pokeoffice.ar",
        "codigo": "747191",
        "spreadsheet_id": "",
    },
    {
        "negocio": "Bruno Express Reparto",
        "tenant_id": "5f8c3093-b703-4c67-a4e0-7904ed084c9d",
        "email": "bruno.reparto.test@pokeoffice.ar",
        "codigo": "778310",
        "spreadsheet_id": "",
    },
]


async def get_admin_token(client):
    r = await client.post("/api/admin/login", json={"password": ADMIN_PASS})
    r.raise_for_status()
    return r.json()["token"]


async def main():
    print(f"\n=== Completar Seed — {API_URL} ===\n")
    tokens_resultado = []

    async with httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT) as client:
        admin_token = await get_admin_token(client)
        print(f"✓ Admin autenticado\n")

        for t in TENANTS:
            print(f"[{t['negocio']}]")

            # 1. Si hay spreadsheet_id, vincular
            if t["spreadsheet_id"]:
                r = await client.patch(
                    f"/api/admin/tenants/{t['tenant_id']}/vincular-planilla",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"spreadsheet_id": t["spreadsheet_id"]},
                )
                if r.status_code < 400:
                    print(f"  ✓ Planilla vinculada: {t['spreadsheet_id']}")
                else:
                    print(f"  ⚠ Error vinculando: {r.text[:100]}")
            else:
                print(f"  ⏭ Sin planilla — agregar spreadsheet_id en este script")

            # 2. Registrar usuario con código de invitación
            # Primero generar código nuevo (el anterior puede haber expirado)
            r = await client.post(
                f"/api/admin/tenants/{t['tenant_id']}/invite",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"email": t["email"]},
            )
            if r.status_code >= 400:
                print(f"  ⚠ No pudo generar invitación: {r.text[:100]}")
                continue
            nuevo_codigo = r.json()["codigo"]
            print(f"  → Código de invitación: {nuevo_codigo}")

            # 3. Verificar código y obtener token
            r = await client.post("/auth/verificar", json={
                "email": t["email"],
                "codigo": nuevo_codigo,
            })
            if r.status_code >= 400:
                print(f"  ✗ Error al verificar: {r.text[:100]}")
                continue

            user_token = r.json()["token"]
            print(f"  ✓ Usuario registrado")
            tokens_resultado.append({
                "negocio": t["negocio"],
                "tenant_id": t["tenant_id"],
                "status": "OK",
                "token": user_token,
            })

            await asyncio.sleep(0.5)

    # Guardar tokens para stress_test.py
    tokens_file = HERE / "tenant_tokens.json"
    with open(tokens_file, "w", encoding="utf-8") as f:
        json.dump(tokens_resultado, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Tokens guardados en {tokens_file}")
    print(f"✅ {len(tokens_resultado)}/5 tenants listos")
    print()
    print("PRÓXIMOS PASOS:")
    print("1. Crear 5 Google Sheets y compartirlas con:")
    print("   pokeoffice-agent@pokeoffice.iam.gserviceaccount.com (como Editor)")
    print("2. Copiar el spreadsheet_id de cada URL:")
    print("   https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit")
    print("3. Agregar los IDs en TENANTS[] de este script y re-ejecutar")
    print("4. Luego ejecutar: python stress_test.py")


if __name__ == "__main__":
    asyncio.run(main())
