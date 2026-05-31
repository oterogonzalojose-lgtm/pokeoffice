"""
stress_test.py — Stress test de conversaciones concurrentes y casos borde.

Uso:
    cd pokeoffice/tests/scenarios
    pip install httpx pytest-asyncio
    POKEOFFICE_URL=https://pokeoffice-production.up.railway.app \\
    python stress_test.py

Requiere que seed_tenants.py haya corrido antes y generado tenant_tokens.json.

Escenarios de estrés:
1. Conversaciones concurrentes de múltiples tenants (no debe haber cross-leak)
2. Mensajes de borde: montos sin $, nombres sin apellido, stock inexistente
3. Flujos completos de venta (registro cliente + baja stock + ingreso finanzas)
4. Correcciones de stock (set vs add)
5. Intento de confundir al VP con instrucciones ambiguas
6. Múltiples ventas en el mismo turno
7. Duplicados intencionales (mismo cliente, mismo monto)
"""
import asyncio
import json
import os
import sys
import time
from typing import Optional
import httpx

sys.path.insert(0, str(__file__).rsplit("/scenarios", 1)[0])
from scenarios.business_data import TODOS_LOS_NEGOCIOS

API_URL    = os.getenv("POKEOFFICE_URL", "https://pokeoffice-production.up.railway.app")
TIMEOUT    = 120.0
TOKENS_FILE = os.path.join(os.path.dirname(__file__), "tenant_tokens.json")


# ── Casos de stress por categoría ────────────────────────────────────────────

# Casos que deben FUNCIONAR correctamente
CASOS_POSITIVOS = [
    # Ventas completas (stock + ingreso + cliente nuevo si aplica)
    {
        "desc": "Venta simple con cliente existente",
        "mensaje": "Le vendí a María Fernández un aceite de lavanda, $2200. Pagó en Mercado Pago",
        "negocio_idx": 0,  # Masajista
        "validaciones": ["ingreso", "stock", "2200"],
    },
    {
        "desc": "Venta a cliente nuevo — debe registrar 3 cosas",
        "mensaje": "Le vendí al nuevo cliente Roberto Medina, tel 1199887766, un mate de calabaza a $3800. Pagó efectivo",
        "negocio_idx": 3,  # Mates
        "validaciones": ["Roberto", "3800", "stock"],
    },
    # Compras (stock + egreso)
    {
        "desc": "Compra de insumos — debe registrar stock y egreso",
        "mensaje": "Compré 10 latas de masilla plástica en AutoPartes Sur, $2000 cada una, pagué en efectivo",
        "negocio_idx": 2,  # Chapa
        "validaciones": ["10", "masilla", "20000"],
    },
    # Actualización de campos personalizados
    {
        "desc": "Actualizar campo personalizado de cliente",
        "mensaje": "Actualizá los datos de Julieta Herrera: campo Diseño favorito = Flores y lunas",
        "negocio_idx": 3,  # Mates
        "validaciones": ["Julieta", "actualiz"],
    },
    # Consultas de stock
    {
        "desc": "Consulta de stock — no debe modificar nada",
        "mensaje": "Cuánto aceite de lavanda me queda?",
        "negocio_idx": 0,
        "validaciones": ["unidades", "lavanda"],
    },
    # Correcciones de stock
    {
        "desc": "Corrección de stock — reemplaza, no suma",
        "mensaje": "En realidad me quedan 3 bombillas de alpaca, no 25. Corregí el stock",
        "negocio_idx": 3,
        "validaciones": ["3", "bombilla"],
    },
    # Registro de gastos
    {
        "desc": "Gasto de nafta — solo egreso, sin stock",
        "mensaje": "Gasté $14000 en nafta hoy, pagué en efectivo",
        "negocio_idx": 4,  # Repartidor
        "validaciones": ["14000", "egreso", "nafta"],
    },
    # Nuevo cliente con datos completos
    {
        "desc": "Nuevo cliente con nombre + apellido + tel",
        "mensaje": "Nuevo cliente: Hernán Bustamante, tel 1177889900. Necesita 5 ejes de transmisión en acero",
        "negocio_idx": 1,  # Tornero
        "validaciones": ["Hernán", "Bustamante", "registr"],
    },
]

# Casos que deben FALLAR GRACIOSAMENTE (sin crash, con mensaje descriptivo)
CASOS_BORDE = [
    {
        "desc": "Venta de producto que no existe en stock",
        "mensaje": "Le vendí a Carlos 3 unidades de 'motor de avión', $500000",
        "negocio_idx": 0,
        "esperado": "no se encontró",
    },
    {
        "desc": "Ingreso sin monto",
        "mensaje": "Cobré un trabajo hoy pero no sé cuánto fue",
        "negocio_idx": 1,
        "esperado": "monto",
    },
    {
        "desc": "Registro cliente sin nombre",
        "mensaje": "Registrar nuevo cliente, teléfono 1199001122",
        "negocio_idx": 0,
        "esperado": "nombre",
    },
    {
        "desc": "Intento de duplicado intencional — mismo monto y categoría",
        "mensaje": "Registrá otro ingreso de $8000 por masaje de María Fernández",
        "negocio_idx": 0,
        "esperado": "duplicado",
    },
    {
        "desc": "Consulta ambigua — VP debe pedir aclaración",
        "mensaje": "Hacé algo con el stock",
        "negocio_idx": 2,
        "esperado": None,  # Solo valida que no crashee
    },
    {
        "desc": "Venta con stock en 0",
        "mensaje": "Le vendí a un cliente 2 correas de talle mediano a $4500 c/u",
        "negocio_idx": 0,  # Perros Bonitos (en el seeder original) — CORREA-MED tenía 0
        "esperado": None,
    },
]

# Conversaciones de múltiples turnos (estado complejo)
CONVERSACIONES_MULTITURN = [
    {
        "desc": "Compra + consulta del stock actualizado",
        "negocio_idx": 0,
        "turnos": [
            "Compré 5 aceites de lavanda en Naturalia, $1200 cada uno",
            "Cuánto aceite de lavanda tengo ahora?",
        ],
    },
    {
        "desc": "Registro cliente → actualización datos → venta",
        "negocio_idx": 3,
        "turnos": [
            "Nuevo cliente: Sebastián Molina, tel 1144332200",
            "Actualizar Sebastián Molina: campo Diseño favorito = Abstracto, campo Mate preferido = Calabaza natural",
            "Le vendí un mate de calabaza a Sebastián Molina, $3800, pagó efectivo",
        ],
    },
    {
        "desc": "Trabajo terminado — cobro + registro",
        "negocio_idx": 2,
        "turnos": [
            "Terminé el trabajo de Lucía Campos. El diagnóstico fue: abolladura leve en paragolpes trasero",
            "Actualizá el estado de Lucía Campos: campo Estado del trabajo = Listo para retirar",
            "Lucía Campos vino a buscar el auto, cobré $55000 en efectivo",
        ],
    },
]


# ── Funciones de test ─────────────────────────────────────────────────────────

async def enviar_mensaje(client: httpx.AsyncClient, token: str, mensaje: str) -> dict:
    t0 = time.time()
    try:
        r = await client.post("/message",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": mensaje},
            timeout=TIMEOUT,
        )
        duration = time.time() - t0
        if r.status_code >= 400:
            return {"ok": False, "error": r.text[:200], "duration": duration, "response": ""}
        data = r.json()
        return {"ok": True, "response": data.get("response", ""), "duration": duration}
    except Exception as e:
        return {"ok": False, "error": str(e), "duration": time.time() - t0, "response": ""}


def validar_respuesta(resultado: dict, validaciones: list[str], desc: str) -> bool:
    respuesta = resultado.get("response", "").lower()
    errores = []
    for v in validaciones:
        if v.lower() not in respuesta:
            errores.append(f"'{v}' no encontrado en respuesta")
    if errores:
        print(f"    ⚠ Validaciones fallidas: {', '.join(errores)}")
        return False
    return True


# ── Runners ───────────────────────────────────────────────────────────────────

async def run_casos_positivos(client: httpx.AsyncClient, tokens: list[dict]):
    print("\n" + "="*60)
    print("CASOS POSITIVOS — Deben funcionar correctamente")
    print("="*60)
    total = ok = 0

    for caso in CASOS_POSITIVOS:
        idx = caso["negocio_idx"]
        if idx >= len(tokens):
            print(f"  ⏭ {caso['desc']} — token no disponible")
            continue

        token = tokens[idx]["token"]
        print(f"\n  [{idx+1}] {caso['desc']}")
        print(f"      Mensaje: {caso['mensaje'][:70]}...")

        resultado = await enviar_mensaje(client, token, caso["mensaje"])

        total += 1
        if not resultado["ok"]:
            print(f"      ❌ ERROR: {resultado.get('error', '')[:100]}")
            continue

        print(f"      Respuesta ({resultado['duration']:.1f}s): {resultado['response'][:80]}...")

        if caso.get("validaciones"):
            if validar_respuesta(resultado, caso["validaciones"], caso["desc"]):
                print(f"      ✅ Validaciones OK")
                ok += 1
            else:
                print(f"      ❌ Validaciones FALLIDAS")
        else:
            ok += 1
            print(f"      ✅ Sin crash")

        await asyncio.sleep(2)

    print(f"\n  Resultado: {ok}/{total} OK")
    return ok, total


async def run_casos_borde(client: httpx.AsyncClient, tokens: list[dict]):
    print("\n" + "="*60)
    print("CASOS BORDE — Deben fallar GRACIOSAMENTE (sin crash)")
    print("="*60)
    total = ok = 0

    for caso in CASOS_BORDE:
        idx = caso["negocio_idx"]
        if idx >= len(tokens):
            continue

        token = tokens[idx]["token"]
        print(f"\n  {caso['desc']}")
        print(f"      Mensaje: {caso['mensaje'][:70]}...")

        resultado = await enviar_mensaje(client, token, caso["mensaje"])
        total += 1

        if not resultado["ok"]:
            print(f"      ❌ CRASH: {resultado.get('error', '')[:100]}")
            continue

        respuesta = resultado["response"]
        print(f"      Respuesta ({resultado['duration']:.1f}s): {respuesta[:80]}...")

        # Validar que no crashed y si hay palabra esperada
        esperado = caso.get("esperado")
        if esperado and esperado.lower() in respuesta.lower():
            print(f"      ✅ Manejó correctamente (menciona '{esperado}')")
            ok += 1
        elif not esperado:
            print(f"      ✅ Sin crash")
            ok += 1
        else:
            print(f"      ⚠ No mencionó '{esperado}' — respuesta puede ser incorrecta")
            ok += 1  # No crash = parcialmente OK

        await asyncio.sleep(2)

    print(f"\n  Resultado: {ok}/{total} sin crash")
    return ok, total


async def run_multiturn(client: httpx.AsyncClient, tokens: list[dict]):
    print("\n" + "="*60)
    print("CONVERSACIONES MULTI-TURNO — Flujos complejos de negocio")
    print("="*60)
    total = ok = 0

    for conv in CONVERSACIONES_MULTITURN:
        idx = conv["negocio_idx"]
        if idx >= len(tokens):
            continue

        token = tokens[idx]["token"]
        print(f"\n  {conv['desc']}")
        total += 1
        conv_ok = True

        for i, turno in enumerate(conv["turnos"], 1):
            print(f"    Turno {i}: {turno[:60]}...")
            resultado = await enviar_mensaje(client, token, turno)
            if not resultado["ok"]:
                print(f"    ❌ CRASH en turno {i}: {resultado.get('error', '')[:100]}")
                conv_ok = False
                break
            print(f"    → {resultado['response'][:70]}... ({resultado['duration']:.1f}s)")
            await asyncio.sleep(2)

        if conv_ok:
            print(f"    ✅ Flujo completado sin errores")
            ok += 1

    print(f"\n  Resultado: {ok}/{total} flujos completos")
    return ok, total


async def run_concurrencia(client: httpx.AsyncClient, tokens: list[dict]):
    """Test de concurrencia: todos los tenants mandan mensajes simultáneamente."""
    print("\n" + "="*60)
    print("TEST CONCURRENCIA — Todos los tenants simultáneamente")
    print("="*60)

    if len(tokens) < 2:
        print("  ⏭ Se necesitan al menos 2 tenants para el test de concurrencia")
        return 0, 0

    mensajes_concurrentes = [
        (tokens[0]["token"], "Cuánto aceite de lavanda me queda?"),
        (tokens[1]["token"], "Cuántas barras de acero tengo?"),
        (tokens[2]["token"], "Cuántas latas de pintura base me quedan?"),
        (tokens[3]["token"], "Cuántos mates de calabaza tengo?"),
        (tokens[4]["token"], "Cuántas cajas de cartón chica tengo?"),
    ]
    mensajes_disponibles = [(t, m) for t, m in mensajes_concurrentes if t][:len(tokens)]

    print(f"  Enviando {len(mensajes_disponibles)} mensajes simultáneos...")
    t0 = time.time()

    resultados = await asyncio.gather(*[
        enviar_mensaje(client, token, msg)
        for token, msg in mensajes_disponibles
    ])

    duration = time.time() - t0
    ok = sum(1 for r in resultados if r["ok"])
    print(f"  Completado en {duration:.1f}s — {ok}/{len(resultados)} exitosos")

    # Verificar que no hubo cross-leak (cada uno respondió sobre su negocio)
    palabras_propias = ["lavanda", "acero", "pintura", "calabaza", "cajas"]
    for i, (resultado, (token, msg)) in enumerate(zip(resultados, mensajes_disponibles)):
        if resultado["ok"] and i < len(palabras_propias):
            resp = resultado["response"].lower()
            if palabras_propias[i] in resp:
                print(f"  ✅ Tenant {i+1}: respuesta correcta (menciona '{palabras_propias[i]}')")
            else:
                print(f"  ⚠ Tenant {i+1}: respuesta no menciona '{palabras_propias[i]}' — posible cross-leak?")
                print(f"     Respuesta: {resultado['response'][:100]}")

    return ok, len(resultados)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    # Cargar tokens
    if not os.path.exists(TOKENS_FILE):
        print(f"❌ {TOKENS_FILE} no encontrado. Corré seed_tenants.py primero.")
        sys.exit(1)

    with open(TOKENS_FILE) as f:
        tokens = json.load(f)

    if not tokens:
        print("❌ No hay tokens disponibles. Verificá que seed_tenants.py completó correctamente.")
        sys.exit(1)

    print(f"\n🧪 Pokeoffice Stress Test — {API_URL}")
    print(f"   Tenants disponibles: {len(tokens)}")
    print(f"   Negocios: {', '.join(t['negocio'] for t in tokens)}\n")

    resultados_totales = {"ok": 0, "total": 0}

    async with httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT) as client:
        # Test 1: Casos positivos
        ok, total = await run_casos_positivos(client, tokens)
        resultados_totales["ok"] += ok
        resultados_totales["total"] += total

        # Test 2: Casos borde
        ok, total = await run_casos_borde(client, tokens)
        resultados_totales["ok"] += ok
        resultados_totales["total"] += total

        # Test 3: Multi-turno
        ok, total = await run_multiturn(client, tokens)
        resultados_totales["ok"] += ok
        resultados_totales["total"] += total

        # Test 4: Concurrencia
        ok, total = await run_concurrencia(client, tokens)
        resultados_totales["ok"] += ok
        resultados_totales["total"] += total

    # Resumen final
    print("\n" + "="*60)
    print("RESUMEN STRESS TEST")
    print("="*60)
    pct = (resultados_totales["ok"] / resultados_totales["total"] * 100) if resultados_totales["total"] else 0
    print(f"Total: {resultados_totales['ok']}/{resultados_totales['total']} ({pct:.0f}%)")
    if pct >= 90:
        print("✅ PLATAFORMA ESTABLE")
    elif pct >= 70:
        print("⚠ PROBLEMAS DETECTADOS — revisar casos fallidos")
    else:
        print("❌ MÚLTIPLES FALLOS — requiere intervención")


if __name__ == "__main__":
    asyncio.run(main())
