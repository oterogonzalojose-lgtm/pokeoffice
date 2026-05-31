import re
from .base import BaseAgent, _client
from mcp import sheets_client as sh


class AtencionClienteAgent(BaseAgent):
    agent_id     = "atencion_cliente"
    display_name = "Recepcionista"

    def system_prompt(self) -> str:
        return """Sos la recepcionista de un pequeño negocio. Gestionás clientes, turnos y comunicaciones con acceso directo a Google Sheets.

REGLAS CRÍTICAS:
1. NUNCA inventes ni asumas datos de un cliente (nombre, teléfono, email, etc.). Si faltan datos, pedílos explícitamente.
2. Antes de registrar un cliente nuevo, verificá que no exista ya en el sistema (buscá por nombre o teléfono).
3. Si la tarea está incompleta o ambigua, hacé UNA sola pregunta concreta para despejar la duda. No hagas varias preguntas a la vez.
4. Confirmá cada acción ejecutada con un resumen claro: qué hiciste, con qué datos, y el resultado.

FORMATO DE RESPUESTA:
- Acción realizada: [qué hiciste]
- Datos: [los datos concretos del cliente]
- Estado: [confirmado / pendiente / error]
- Si hay mensaje para cliente: marcalo como → MENSAJE PARA CLIENTE: [texto]

DATOS MÍNIMOS PARA REGISTRAR UN CLIENTE:
- Nombre y apellido (obligatorio)
- Teléfono o email (al menos uno)
- El resto (dirección, notas) es opcional

NO hagas:
- No confirmes acciones que no se ejecutaron
- No inventes datos que no te pasaron
- No mandes mensajes a clientes sin confirmación del jefe

Respondé siempre en español, de forma directa y sin rodeos."""

    def tools(self) -> list[dict]:
        return []  # El agente ejecuta acciones directamente sin depender del tool_use de Claude

    async def run(self, task: str, broadcast=None) -> str:
        """
        Detecta el intent y ejecuta la acción directamente en Sheets,
        luego usa Claude solo para formatear la respuesta.
        """
        task_lower = task.lower()

        # ── Agregar cliente ───────────────────────────────────────────────────
        if any(w in task_lower for w in ["agreg", "añad", "nuevo cliente", "alta", "registr"]):
            datos = self._extraer_datos_cliente(task)

            # Validar datos mínimos antes de escribir en Sheets
            if not datos.get("nombre"):
                contexto = (
                    "No pude identificar el nombre del cliente en la instrucción. "
                    "Por favor indicá: nombre y apellido (obligatorio) + teléfono o email (al menos uno)."
                )
            else:
                # Verificar duplicado por nombre Y por teléfono antes de registrar
                await self._emit(broadcast, "working", "Verificando si el cliente ya existe...")
                nombre_completo = f"{datos['nombre']} {datos['apellido']}".strip()
                try:
                    existentes = sh.buscar_cliente(nombre_completo)
                    # Si no encontró por nombre, buscar también por teléfono
                    if not existentes and datos.get("telefono"):
                        existentes = sh.buscar_cliente(datos["telefono"])
                except Exception:
                    existentes = []

                if existentes:
                    c = existentes[0]
                    nombre_existente = f"{c['nombre']} {c['apellido']}".strip()
                    if nombre_existente.lower() == nombre_completo.lower():
                        # Mismo nombre — duplicado directo
                        contexto = (
                            f"El cliente '{nombre_completo}' ya existe en el sistema "
                            f"(ID #{c['id']}, Tel: {c['telefono'] or 'sin tel'}, Email: {c['email'] or 'sin email'}). "
                            f"No se registró de nuevo. ¿Querés actualizar algún dato?"
                        )
                    else:
                        # Nombre diferente pero mismo teléfono — conflicto, preguntar al jefe
                        contexto = (
                            f"Ya hay un cliente registrado con el teléfono {datos['telefono']}: "
                            f"'{nombre_existente}' (ID #{c['id']}). "
                            f"¿Querés registrar a '{nombre_completo}' como cliente nuevo igualmente, "
                            f"o actualizar los datos del registro existente?"
                        )
                else:
                    await self._emit(broadcast, "working", "Registrando cliente en Sheets...")
                    try:
                        resultado = sh.agregar_cliente(**datos)
                        contexto = f"Acción ejecutada: {resultado}\nDatos registrados: {datos}"
                    except Exception as e:
                        contexto = f"Error al registrar: {e}. Verificá que los datos sean correctos."

        # ── Buscar cliente ────────────────────────────────────────────────────
        elif any(w in task_lower for w in ["buscar", "buscá", "encontrar", "existe", "está cargado"]):
            await self._emit(broadcast, "working", "Buscando en Sheets...")
            query = self._extraer_query(task)
            try:
                found = sh.buscar_cliente(query)
                if found:
                    lines = [f"#{c['id']} {c['nombre']} {c['apellido']} — Tel: {c['telefono']} | Email: {c['email']}" for c in found]
                    contexto = "Clientes encontrados:\n" + "\n".join(lines)
                else:
                    contexto = f"No se encontró ningún cliente con '{query}' en el sistema."
            except Exception as e:
                contexto = f"Error al buscar: {e}"

        # ── Listar clientes ───────────────────────────────────────────────────
        elif any(w in task_lower for w in ["listar", "mostrar", "lista", "ver client", "cuántos client", "cuantos client", "todos los client"]):
            await self._emit(broadcast, "working", "Leyendo clientes de Sheets...")
            try:
                clientes = sh.listar_clientes()
                if clientes:
                    lines = [f"#{c['id']} {c['nombre']} {c['apellido']} — Tel: {c['telefono']}" for c in clientes]
                    contexto = f"Clientes registrados ({len(clientes)}):\n" + "\n".join(lines)
                else:
                    contexto = "No hay clientes registrados aún."
            except Exception as e:
                contexto = f"Error al leer clientes: {e}"

        # ── Actualizar campo de cliente existente ─────────────────────────────
        elif any(w in task_lower for w in ["actualiz", "modific", "cambi", "poné", "pone", "anotá", "anota"]):
            await self._emit(broadcast, "working", "Actualizando datos del cliente...")

            # Extraer nombre del cliente: "de/para/actualizar NOMBRE"
            m_nombre = re.search(
                r"(?:de|para|actualizar|actualiz[aá]r?)\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)+)",
                task, re.IGNORECASE
            )
            nombre_cliente = m_nombre.group(1).strip() if m_nombre else ""

            # Extraer pares campo = valor (formato: "campo NOMBRE = VALOR")
            partes_campo = re.split(r"\bcampo\b", task, flags=re.IGNORECASE)
            pares = []
            for parte in partes_campo[1:]:
                m = re.match(r"\s*([^=]+?)\s*=\s*(.+?)(?:\s*,\s*$|\s*$)", parte.strip(), re.DOTALL)
                if m:
                    campo = m.group(1).strip().strip("'\"")
                    valor = m.group(2).strip().strip("'\"").rstrip(",").strip()
                    if campo and valor:
                        pares.append((campo, valor))

            if not nombre_cliente:
                contexto = "No pude identificar el cliente a actualizar. Indicá el nombre completo."
            elif not pares:
                contexto = (
                    "No pude identificar qué campo actualizar. "
                    "Usá el formato: 'campo [Nombre del campo] = [Valor]'"
                )
            else:
                resultados = []
                for campo, valor in pares:
                    await self._emit(broadcast, "working", f"Actualizando '{campo}'...")
                    try:
                        r = sh.actualizar_campo_cliente(nombre_cliente, campo, valor)
                        resultados.append(r)
                    except Exception as e:
                        resultados.append(f"Error al actualizar '{campo}': {e}")
                contexto = "\n".join(resultados)

        # ── Tarea de comunicación (redactar mensajes) ─────────────────────────
        else:
            await self._emit(broadcast, "thinking", "Preparando respuesta...")
            contexto = None

        # Claude formatea la respuesta final
        await self._emit(broadcast, "thinking", "Redactando respuesta...")
        if contexto:
            prompt = f"Contexto de la acción ejecutada:\n{contexto}\n\nTarea original: {task}\n\nRespondé confirmando la acción o presentando la información de forma clara."
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

    # ── Helpers de extracción ─────────────────────────────────────────────────

    def _extraer_datos_cliente(self, task: str) -> dict:
        datos = {"nombre": "", "apellido": "", "telefono": "", "email": "", "comentarios": ""}

        # Email
        m = re.search(r"[\w.+-]+@[\w-]+\.\w+", task)
        if m:
            datos["email"] = m.group()

        # Teléfono (solo dígitos, sin espacios para evitar capturar texto adyacente)
        m = re.search(r"\b(\+?[\d]{8,15})\b", task)
        if m:
            datos["telefono"] = m.group().strip()

        # Nombre — PRIORIDAD 1: etiqueta explícita "Nombre:" (formato del VP estructurado)
        # El VP envía: "- Nombre: Fernando Barrios - Teléfono: ..."
        m = re.search(
            r"[Nn]ombre:\s*([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)*)",
            task
        )
        if not m:
            # PRIORIDAD 2: nombre propio después de "cliente" — SIN IGNORECASE para que
            # [A-ZÁÉÍÓÚÑ] solo matchee mayúsculas y no capture "con", "los", "de", etc.
            m = re.search(
                r"(?:(?:al|nuevo|del?|para)\s+)?cliente:?\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)",
                task
            )
        if m:
            partes = m.group(1).strip().split()
            datos["nombre"] = partes[0]
            if len(partes) > 1:
                datos["apellido"] = " ".join(partes[1:])

        return datos

    def _extraer_query(self, task: str) -> str:
        # Extrae lo que viene después de "buscar", "encontrar", etc.
        m = re.search(r"(?:buscar|buscá|encontrar|cliente)\s+(?:a\s+)?([A-Za-záéíóúñÁÉÍÓÚÑ\s]+?)(?:\s*,|\s*$)", task, re.IGNORECASE)
        return m.group(1).strip() if m else task
