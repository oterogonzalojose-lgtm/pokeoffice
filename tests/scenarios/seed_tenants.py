"""
seed_tenants.py — Crea y popula los 5 tenants de testing en el entorno indicado.

Uso:
    cd pokeoffice/tests/scenarios
    pip install httpx
    POKEOFFICE_URL=https://pokeoffice-production.up.railway.app \\
    ADMIN_PASSWORD=tu_password \\
    python seed_tenants.py

El script:
1. Crea 5 tenants via admin API
2. Crea una planilla Google Sheets para cada uno
3. Genera códigos de invitación
4. Registra usuarios automáticamente
5. Corre onboarding
6. Agrega columnas personalizadas
7. Popula clientes con datos específicos del negocio
8. Registra stock inicial
9. Registra movimientos financieros iniciales

Los usuarios creados tienen email: {negocio}@test.pokeoffice.ar
Para simular conversaciones usar stress_test.py después.
"""
import asyncio
import os
import json
import sys
from typing import Optional
import httpx

# Importar datos de negocios
sys.path.insert(0, str(__file__).rsplit("/scenarios", 1)[0])
from scenarios.business_data import TODOS_LOS_NEGOCIOS

API_URL      = os.getenv("POKEOFFICE_URL", "https://pokeoffice-production.up.railway.app")
ADMIN_PASS   = os.getenv("ADMIN_PASSWORD", "")
TIMEOUT      = 60.0  # segundos


# ── Cliente HTTP ──────────────────────────────────────────────────────────────

async def get_admin_token(client: httpx.AsyncClient) -> str:
    r = await client.post("/api/admin/login", json={"password": ADMIN_PASS})
    r.raise_for_status()
    return r.json()["token"]


async def admin(client: httpx.AsyncClient, token: str, method: str, path: str, **kwargs):
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.request(method, path, headers=headers, **kwargs)
    if r.status_code >= 400:
        print(f"  ⚠ {method} {path} → {r.status_code}: {r.text[:200]}")
        return None
    return r.json()


async def user_request(client: httpx.AsyncClient, token: str, method: str, path: str, **kwargs):
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.request(method, path, headers=headers, **kwargs)
    if r.status_code >= 400:
        print(f"  ⚠ {method} {path} → {r.status_code}: {r.text[:200]}")
        return None
    return r.json()


# ── Flujo por tenant ──────────────────────────────────────────────────────────

async def crear_tenant(client: httpx.AsyncClient, admin_token: str, negocio: dict) -> Optional[dict]:
    perfil = negocio["perfil"]
    print(f"\n{'='*60}")
    print(f"  Creando tenant: {perfil['nombre_negocio']}")
    print(f"{'='*60}")

    # 1. Crear tenant
    tenant = await admin(client, admin_token, "POST", "/api/admin/tenants", json={
        "email": perfil["email_admin"],
        "nombre_negocio": perfil["nombre_negocio"],
        "plan": "starter",
    })
    if not tenant:
        print(f"  ✗ No se pudo crear el tenant")
        return None
    tid = tenant["id"]
    print(f"  ✓ Tenant creado: {tid[:8]}...")

    # 2. Crear planilla Google Sheets
    print(f"  → Creando planilla...")
    sheet_resp = await admin(client, admin_token, "POST", f"/api/admin/tenants/{tid}/crear-planilla")
    if sheet_resp:
        print(f"  ✓ Planilla creada")
    else:
        print(f"  ⚠ No se pudo crear planilla — continuando sin ella")

    # 3. Crear invitación para el usuario del negocio
    print(f"  → Generando invitación...")
    invite = await admin(client, admin_token, "POST", f"/api/admin/tenants/{tid}/invite",
                         json={"email": perfil["email_admin"]})
    if not invite:
        print(f"  ✗ No se pudo crear invitación")
        return None
    codigo = invite["codigo"]
    print(f"  ✓ Código de invitación: {codigo}")

    return {"tenant_id": tid, "codigo": codigo, "negocio": negocio}


async def registrar_usuario(client: httpx.AsyncClient, tenant_info: dict) -> Optional[str]:
    """Registra el usuario y retorna su JWT."""
    perfil = tenant_info["negocio"]["perfil"]
    email  = perfil["email_admin"]
    codigo = tenant_info["codigo"]

    # Verificar código
    r = await client.post("/api/auth/verify", json={
        "email": email,
        "codigo": codigo,
        "nombre": perfil["nombre_jefe"],
    })
    if r.status_code >= 400:
        print(f"  ✗ Error verificando código: {r.text[:200]}")
        return None

    data = r.json()
    token = data.get("token")
    print(f"  ✓ Usuario registrado")
    return token


async def configurar_negocio(client: httpx.AsyncClient, user_token: str, negocio: dict):
    """Completa el onboarding del negocio."""
    perfil = negocio["perfil"]

    r = await client.post("/config/onboarding",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "nombre_negocio": perfil["nombre_negocio"],
            "nombre_jefe":    perfil["nombre_jefe"],
            "tipo_negocio":   perfil["tipo_negocio"],
            "moneda":         perfil["moneda"],
            "sector":         perfil.get("sector", ""),
            "descripcion":    perfil.get("descripcion", ""),
        }
    )
    if r.status_code < 400:
        print(f"  ✓ Onboarding completado")
    else:
        print(f"  ⚠ Error en onboarding: {r.text[:100]}")


async def enviar_mensaje_vp(client: httpx.AsyncClient, user_token: str, mensaje: str) -> str:
    """Envía un mensaje al VP y retorna la respuesta."""
    r = await client.post("/message",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"message": mensaje},
        timeout=90.0,
    )
    if r.status_code >= 400:
        return f"ERROR: {r.text[:100]}"
    return r.json().get("response", "")


async def agregar_columnas_personalizadas(client: httpx.AsyncClient, user_token: str, columnas: list[str], hoja: str = "Clientes"):
    """Agrega columnas personalizadas al sheet via el VP."""
    print(f"  → Agregando columnas personalizadas: {', '.join(columnas)}")
    for columna in columnas:
        respuesta = await enviar_mensaje_vp(
            client, user_token,
            f"Agregá la columna '{columna}' a la hoja {hoja}"
        )
        ok = "✓" in respuesta or "agrega" in respuesta.lower() or "column" in respuesta.lower()
        print(f"    {'✓' if ok else '?'} {columna}: {respuesta[:60]}...")
        await asyncio.sleep(1)


async def poblar_clientes(client: httpx.AsyncClient, user_token: str, clientes: list[dict]):
    """Registra clientes y actualiza sus campos personalizados."""
    print(f"  → Registrando {len(clientes)} clientes...")
    for i, c in enumerate(clientes, 1):
        nombre_completo = f"{c['nombre']} {c['apellido']}"
        tel  = c.get("telefono", "")
        mail = c.get("email", "")

        # Registrar cliente
        msg = f"Registrar nuevo cliente: {nombre_completo}"
        if tel:
            msg += f", teléfono: {tel}"
        if mail:
            msg += f", email: {mail}"

        respuesta = await enviar_mensaje_vp(client, user_token, msg)
        print(f"    [{i:02d}] {nombre_completo}: {respuesta[:60]}...")
        await asyncio.sleep(1.5)

        # Actualizar campos personalizados
        if c.get("campos"):
            campos_str = ", ".join(
                f"campo {k} = {v}" for k, v in c["campos"].items()
            )
            msg_update = f"Actualizar {nombre_completo}: {campos_str}"
            await enviar_mensaje_vp(client, user_token, msg_update)
            await asyncio.sleep(1)


async def poblar_stock(client: httpx.AsyncClient, user_token: str, stock: list[dict]):
    """Registra el stock inicial del negocio."""
    print(f"  → Registrando {len(stock)} productos en stock...")
    for item in stock:
        msg = (f"Registrá en stock: {item['unidades']} unidades de '{item['descripcion']}' "
               f"(código: {item['codigo']}), precio de venta ${item['precio_venta']}, "
               f"costo ${item['costo_compra']}, proveedor: {item['proveedor']}")
        respuesta = await enviar_mensaje_vp(client, user_token, msg)
        ok = "✓" in respuesta or "stock" in respuesta.lower()
        print(f"    {'✓' if ok else '?'} {item['codigo']}: {respuesta[:60]}...")
        await asyncio.sleep(1.5)


async def registrar_finanzas(client: httpx.AsyncClient, user_token: str, movimientos: list[dict]):
    """Registra los movimientos financieros iniciales."""
    print(f"  → Registrando {len(movimientos)} movimientos financieros...")
    for mov in movimientos:
        if mov["ingreso"] > 0:
            msg = f"Registrá un ingreso de ${mov['ingreso']:,.0f} por concepto '{mov['desc']}', categoría {mov['cat']}, cuenta: {mov['cuenta']}"
        else:
            msg = f"Registrá un egreso de ${mov['egreso']:,.0f} por concepto '{mov['desc']}', categoría {mov['cat']}, cuenta: {mov['cuenta']}"

        respuesta = await enviar_mensaje_vp(client, user_token, msg)
        ok = "✓" in respuesta or "registr" in respuesta.lower()
        print(f"    {'✓' if ok else '?'} {mov['desc'][:40]}: {respuesta[:50]}...")
        await asyncio.sleep(1.5)


# ── Runner principal ──────────────────────────────────────────────────────────

async def seed_all():
    if not ADMIN_PASS:
        print("❌ Falta ADMIN_PASSWORD en las variables de entorno")
        print("   Uso: ADMIN_PASSWORD=xxx POKEOFFICE_URL=https://... python seed_tenants.py")
        sys.exit(1)

    print(f"\n🚀 Pokeoffice Seeder — {API_URL}")
    print(f"   Negocios a crear: {len(TODOS_LOS_NEGOCIOS)}")
    print(f"   Modo: completo (clientes + stock + finanzas)\n")

    resultados = []

    async with httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT) as client:
        # Admin token
        try:
            admin_token = await get_admin_token(client)
            print(f"✓ Admin autenticado\n")
        except Exception as e:
            print(f"❌ Error de autenticación admin: {e}")
            sys.exit(1)

        for negocio in TODOS_LOS_NEGOCIOS:
            nombre_negocio = negocio["perfil"]["nombre_negocio"]
            try:
                # Crear tenant
                tenant_info = await crear_tenant(client, admin_token, negocio)
                if not tenant_info:
                    resultados.append({"negocio": nombre_negocio, "status": "ERROR — tenant creation"})
                    continue

                # Registrar usuario
                user_token = await registrar_usuario(client, tenant_info)
                if not user_token:
                    resultados.append({"negocio": nombre_negocio, "status": "ERROR — user registration"})
                    continue

                # Onboarding
                await configurar_negocio(client, user_token, negocio)

                # Columnas personalizadas
                await agregar_columnas_personalizadas(
                    client, user_token,
                    negocio["columnas_clientes"]
                )

                # Clientes
                await poblar_clientes(client, user_token, negocio["clientes"])

                # Stock
                await poblar_stock(client, user_token, negocio["stock"])

                # Finanzas iniciales
                await registrar_finanzas(client, user_token, negocio["finanzas_iniciales"])

                resultados.append({
                    "negocio": nombre_negocio,
                    "status": "OK",
                    "tenant_id": tenant_info["tenant_id"],
                    "token": user_token,
                })
                print(f"\n  ✅ {nombre_negocio} — completado\n")

            except Exception as e:
                print(f"\n  ❌ Error en {nombre_negocio}: {e}\n")
                resultados.append({"negocio": nombre_negocio, "status": f"ERROR: {e}"})

    # Resumen final
    print("\n" + "="*60)
    print("RESUMEN DE SEEDING")
    print("="*60)
    for r in resultados:
        icon = "✅" if r["status"] == "OK" else "❌"
        print(f"{icon} {r['negocio']}: {r['status']}")

    # Guardar tokens para stress_test.py
    tokens_file = os.path.join(os.path.dirname(__file__), "tenant_tokens.json")
    with open(tokens_file, "w") as f:
        json.dump([r for r in resultados if r["status"] == "OK"], f, indent=2)
    print(f"\nTokens guardados en: {tokens_file}")
    print("Ejecutar stress_test.py para simular conversaciones de estrés.")


if __name__ == "__main__":
    asyncio.run(seed_all())
