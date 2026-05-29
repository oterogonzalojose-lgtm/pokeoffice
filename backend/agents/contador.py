import re
from .base import BaseAgent, _client
from mcp import sheets_client as sh


# Palabras clave para detección de intent (prefijos/substrings del español)
_INCOME = [
    "ingreso", "cobro", "venta", "entrada de", "recibí", "cobré",
    "cobr", "vend", "ingres", "factur", "gananci", "recauda",
    "percib", "remuner", "honorari", "recibim", "vendim", "cobram",
]
_EXPENSE = [
    "gasto", "egreso", "pago", "pagué", "pagamos", "salida de",
    "compr", "invert", "gast", "desembols", "erogaci",
    "insumo", "material", "proveedor", "pagam", "gastam",
]
_BALANCE = [
    "balance", "resumen", "situación", "estado financiero",
    "cómo estamos", "como estamos", "liquidez", "total",
]
_BANK = [
    "cuenta bancaria", "banco", "efectivo", "caja",
    "mercado pago", "posición", "billetera",
]


class ContadorAgent(BaseAgent):
    agent_id     = "contador"
    display_name = "Contador"

    def system_prompt(self) -> str:
        return """Sos el contador de un pequeño negocio argentino. Registrás y analizás movimientos financieros con acceso directo a Google Sheets.

REGLAS CRÍTICAS:
1. NUNCA inventes montos, fechas ni descripciones. Si el monto no está claro, pedilo antes de registrar.
2. Todo movimiento debe tener: monto, descripción y categoría. Si falta alguno, solicitálo.
3. Al confirmar un registro, repetí los datos exactos que quedaron asentados.
4. Para balances: mostrá siempre el saldo real del sistema, no hagas estimaciones.

FORMATO DE RESPUESTA para registros:
✓ Registrado: [descripción] — $[monto] — [Ingreso/Egreso]
  En: [hojas donde se registró]
  Saldo actualizado: $[saldo si disponible]

FORMATO DE RESPUESTA para balances/informes:
— Ingresos del período: $X
— Egresos del período: $X
— Resultado neto: $X [✓ positivo / ⚠ negativo]
— Observación: [análisis breve]

FORMATO DE MONTOS: siempre con $ y separador de miles (ej: $12.500, no 12500).

NO hagas:
- No registres el mismo movimiento dos veces
- No redondees montos sin indicarlo
- No inventes categorías que no te pasaron

Respondé en español, de forma concisa y profesional."""

    def tools(self) -> list[dict]:
        return []

    async def run(self, task: str, broadcast=None) -> str:
        task_lower = task.lower()

        # ── Registrar ingreso ─────────────────────────────────────────────────
        if any(w in task_lower for w in _INCOME):
            await self._emit(broadcast, "working", "Registrando ingreso...")
            monto = self._extraer_monto(task)
            desc  = self._extraer_descripcion(task)
            try:
                r1 = sh.registrar_movimiento_finanzas(descripcion=desc, ingreso=monto, categoria="Ingreso")
                contexto = f"Registrado: {r1}"
            except Exception as e:
                contexto = f"Error al registrar: {e}"

        # ── Registrar egreso / gasto ──────────────────────────────────────────
        elif any(w in task_lower for w in _EXPENSE):
            await self._emit(broadcast, "working", "Registrando egreso...")
            monto = self._extraer_monto(task)
            desc  = self._extraer_descripcion(task)
            try:
                r1 = sh.registrar_movimiento_finanzas(descripcion=desc, egreso=monto, categoria="Egreso")
                contexto = f"Registrado: {r1}"
            except Exception as e:
                contexto = f"Error al registrar: {e}"

        # ── Balance / resumen ─────────────────────────────────────────────────
        elif any(w in task_lower for w in _BALANCE):
            await self._emit(broadcast, "working", "Consultando balance...")
            try:
                resumen = sh.obtener_resumen_finanzas()
                cuentas = resumen.get("cuentas", {})
                cuentas_str = " | ".join(
                    f"{k.replace('_',' ').title()}: ${v:,.0f}"
                    for k, v in cuentas.items() if v
                )
                contexto = (
                    f"FINANZAS — Mes actual:\n"
                    f"  Ingresos: ${resumen['ingresos_mes']:,.0f}\n"
                    f"  Egresos:  ${resumen['egresos_mes']:,.0f}\n"
                    f"  Resultado neto: ${resumen['resultado_neto']:,.0f}\n"
                    f"  Total liquidez: ${resumen['total_liquidez']:,.0f}\n"
                    f"  Por cuenta: {cuentas_str or 'sin movimientos'}"
                )
            except Exception as e:
                contexto = f"Error al consultar: {e}"

        # ── Actualizar cuenta bancaria ────────────────────────────────────────
        elif any(w in task_lower for w in _BANK):
            await self._emit(broadcast, "working", "Actualizando posición bancaria...")
            monto  = self._extraer_monto(task)
            cuenta = self._extraer_cuenta(task)
            try:
                r = sh.actualizar_posicion_bancaria(cuenta=cuenta, saldo=monto)
                contexto = f"Actualizado: {r}"
            except Exception as e:
                contexto = f"Error: {e}"

        # ── Fallback: clasificar con Claude si hay monto ──────────────────────
        else:
            contexto = await self._fallback_clasificar(task, task_lower, broadcast)

        await self._emit(broadcast, "thinking", "Redactando respuesta...")
        if contexto:
            prompt = (
                f"Acción ejecutada en el sistema:\n{contexto}\n\n"
                f"Tarea original: {task}\n\n"
                f"Respondé confirmando y analizando brevemente."
            )
        else:
            prompt = task

        result = _client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt(),
            messages=[{"role": "user", "content": prompt}],
        ).content[0].text

        await self._emit(broadcast, "done", result[:100])
        return result

    # ── Fallback cuando ningún keyword hace match ─────────────────────────────

    async def _fallback_clasificar(self, task: str, task_lower: str, broadcast) -> str | None:
        """Si la tarea tiene monto pero no matcheó keywords, usa Claude para clasificar."""
        if not re.search(r"\$?\s*[\d.,]+", task):
            return None  # Sin monto → no es acción contable, responder solo

        await self._emit(broadcast, "thinking", "Clasificando acción...")
        try:
            clasificacion = _client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{
                    "role": "user",
                    "content": (
                        "Respondé con UNA sola palabra (ingreso / egreso / otro):\n"
                        f"¿Esta instrucción registra un ingreso o un egreso?\nTexto: {task}"
                    ),
                }],
            ).content[0].text.strip().lower()
        except Exception:
            return None

        monto = self._extraer_monto(task)
        desc  = self._extraer_descripcion(task)

        if "ingreso" in clasificacion:
            await self._emit(broadcast, "working", "Registrando ingreso...")
            try:
                r1 = sh.registrar_movimiento_finanzas(descripcion=desc, ingreso=monto, categoria="Ingreso")
                return f"Registrado: {r1}"
            except Exception as e:
                return f"Error al registrar ingreso: {e}"

        if "egreso" in clasificacion:
            await self._emit(broadcast, "working", "Registrando egreso...")
            try:
                r1 = sh.registrar_movimiento_finanzas(descripcion=desc, egreso=monto, categoria="Egreso")
                return f"Registrado: {r1}"
            except Exception as e:
                return f"Error al registrar egreso: {e}"

        return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extraer_monto(self, task: str) -> float:
        """
        Parsea montos en español argentino.
        Formatos soportados:
          $5000 | $5.000 | $5.000,50 | $1.500,50 | 5000 | 80000
        Estrategia: buscar primero con $, luego número largo sin separador.
        """
        # Prioridad 1: número precedido por $  (más confiable)
        m = re.search(r"\$\s*([\d.,]+)", task)
        if not m:
            # Prioridad 2: secuencia de 4+ dígitos (evita capturar ítems cortos tipo "3 items")
            m = re.search(r"\b(\d[\d.,]*\d)\b", task)
            # Filtrar resultados menores a 4 dígitos si no hay $
            if m and len(m.group(1).replace(".", "").replace(",", "")) < 4:
                m = None

        if not m:
            # Último recurso: cualquier número
            m = re.search(r"\b(\d+)\b", task)

        if not m:
            return 0.0

        raw = m.group(1).strip().rstrip(".,")

        # Formato AR con punto de miles y coma decimal: 1.500,50 → 1500.50
        if re.match(r"^\d{1,3}(\.\d{3})+(,\d{1,2})?$", raw):
            raw = raw.replace(".", "").replace(",", ".")
        # Solo coma decimal: 1500,50 → 1500.50
        elif re.match(r"^\d+(,\d{1,2})$", raw):
            raw = raw.replace(",", ".")
        # Entero puro o punto decimal anglosajón: 5000 / 5000.50
        else:
            raw = raw.replace(",", "")

        try:
            return float(raw)
        except ValueError:
            return 0.0

    def _extraer_descripcion(self, task: str) -> str:
        desc = re.sub(r"\$?\s*[\d.,]+", "", task)
        desc = re.sub(
            r"\b(registr[aá]|anot[aá]|carg[aá]|ingreso|egreso|gasto|pago|venta"
            r"|compra|hoy|de|un|una|por|al|el|la|los|las|que|se)\b",
            "", desc, flags=re.IGNORECASE,
        )
        return desc.strip(" ,-") or task[:60]

    def _extraer_cuenta(self, task: str) -> str:
        t = task.lower()
        if "mercado pago" in t:    return "Mercado Pago / billetera"
        if "caja de ahorro" in t:  return "Banco (caja de ahorro)"
        if "corriente" in t:       return "Banco (cuenta corriente)"
        if "efectivo" in t or "caja" in t: return "Efectivo en caja"
        return "Banco (cuenta corriente)"
