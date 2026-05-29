import { useState } from 'react'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const TIPOS_NEGOCIO = [
  'Consultorio / Salud',
  'Tienda / Retail',
  'Estudio profesional',
  'Gastronomía',
  'Servicios / Reparaciones',
  'Educación / Clases',
  'Belleza / Estética',
  'Tecnología',
  'Otro',
]

const MONEDAS = [
  { code: 'ARS', label: '$ Peso argentino' },
  { code: 'USD', label: '$ Dólar estadounidense' },
  { code: 'EUR', label: '€ Euro' },
]

// ── Step indicator ────────────────────────────────────────────────────────────
function Steps({ current, total }) {
  return (
    <div className="flex items-center gap-1.5 mb-8">
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full transition-all
            ${i < current ? 'bg-green-500' : i === current ? 'bg-blue-400' : 'bg-[#2a2a4a]'}`}
          />
          {i < total - 1 && (
            <div className={`h-px w-8 transition-all ${i < current ? 'bg-green-500' : 'bg-[#2a2a4a]'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

// ── Campo de input ────────────────────────────────────────────────────────────
function Field({ label, value, onChange, placeholder, type = 'text', hint }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-mono text-gray-400">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="bg-[#0a0a18] border border-[#2a2a4a] focus:border-[#4a4a9a] outline-none
                   px-3 py-2 text-sm text-white font-mono placeholder-gray-600 rounded
                   transition-colors"
      />
      {hint && <p className="text-[10px] font-mono text-gray-600">{hint}</p>}
    </div>
  )
}

// ── Selector de opción ────────────────────────────────────────────────────────
function OptionGrid({ options, value, onChange, columns = 3 }) {
  return (
    <div className={`grid gap-2`} style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
      {options.map(opt => {
        const key   = typeof opt === 'string' ? opt : opt.code
        const label = typeof opt === 'string' ? opt : opt.label
        return (
          <button
            key={key}
            type="button"
            onClick={() => onChange(key)}
            className={`text-xs font-mono px-3 py-2 rounded border text-left transition-all
              ${value === key
                ? 'border-blue-500 bg-[#0d1f3a] text-blue-300'
                : 'border-[#2a2a4a] bg-[#07070f] text-gray-400 hover:border-[#3a3a6a] hover:text-gray-200'}`}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}

// ── Pantallas del wizard ──────────────────────────────────────────────────────
const STEPS = [
  {
    title: 'Bienvenido a Pokeoffice',
    subtitle: 'Tu mini oficina con IA. En 3 pasos configuramos tu equipo.',
    emoji: '🏢',
    render: ({ data, set }) => (
      <div className="flex flex-col gap-4">
        <Field
          label="¿Cuál es tu nombre?"
          value={data.nombre_jefe}
          onChange={v => set('nombre_jefe', v)}
          placeholder="Ej: Martín, Ana..."
          hint="Así te llamará el VP al responder"
        />
        <Field
          label="Nombre de tu negocio"
          value={data.nombre_negocio}
          onChange={v => set('nombre_negocio', v)}
          placeholder="Ej: Consultorio Spinelli, Tienda La Paloma..."
        />
      </div>
    ),
    valid: d => d.nombre_jefe.trim() && d.nombre_negocio.trim(),
  },
  {
    title: '¿A qué te dedicás?',
    subtitle: 'Esto ayuda a que los agentes hablen el lenguaje de tu negocio.',
    emoji: '💼',
    render: ({ data, set }) => (
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-mono text-gray-400">Tipo de negocio</label>
          <OptionGrid
            options={TIPOS_NEGOCIO}
            value={data.tipo_negocio}
            onChange={v => set('tipo_negocio', v)}
            columns={3}
          />
        </div>
        <Field
          label="Contanos brevemente qué hacés (opcional)"
          value={data.descripcion}
          onChange={v => set('descripcion', v)}
          placeholder="Ej: Clínica veterinaria especializada en mascotas pequeñas..."
          hint="Más contexto = respuestas más precisas de los agentes"
        />
      </div>
    ),
    valid: d => d.tipo_negocio.trim(),
  },
  {
    title: 'Configuración final',
    subtitle: 'Casi listo. Solo necesitamos un dato más.',
    emoji: '⚙️',
    render: ({ data, set }) => (
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-mono text-gray-400">Moneda principal</label>
          <OptionGrid
            options={MONEDAS}
            value={data.moneda}
            onChange={v => set('moneda', v)}
            columns={3}
          />
        </div>
        {/* Resumen */}
        <div className="bg-[#0a0a18] border border-[#1e1e3a] rounded p-3 flex flex-col gap-1.5">
          <p className="text-[10px] font-mono text-gray-500 uppercase tracking-wide">Resumen</p>
          <p className="text-sm font-mono text-white">
            <span className="text-gray-500">Jefe: </span>{data.nombre_jefe}
          </p>
          <p className="text-sm font-mono text-white">
            <span className="text-gray-500">Negocio: </span>{data.nombre_negocio}
          </p>
          <p className="text-sm font-mono text-white">
            <span className="text-gray-500">Tipo: </span>{data.tipo_negocio}
          </p>
          <p className="text-sm font-mono text-white">
            <span className="text-gray-500">Moneda: </span>{data.moneda}
          </p>
        </div>
      </div>
    ),
    valid: () => true,
  },
]

// ── Componente principal ──────────────────────────────────────────────────────
export default function Onboarding({ onComplete }) {
  const [step,   setStep]   = useState(0)
  const [saving, setSaving] = useState(false)
  const [data,   setData]   = useState({
    nombre_jefe:    '',
    nombre_negocio: '',
    tipo_negocio:   '',
    descripcion:    '',
    moneda:         'ARS',
  })

  function set(key, value) {
    setData(prev => ({ ...prev, [key]: value }))
  }

  async function handleNext() {
    if (step < STEPS.length - 1) {
      setStep(s => s + 1)
    } else {
      // Guardar y completar
      setSaving(true)
      try {
        await fetch(`${API}/config/onboarding`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify(data),
        })
        onComplete(data)
      } catch {
        onComplete(data)   // guardar localmente aunque falle el backend
      } finally {
        setSaving(false)
      }
    }
  }

  const current = STEPS[step]
  const canNext = current.valid(data)

  return (
    <div className="fixed inset-0 bg-[#04040e] bg-opacity-98 flex items-center justify-center z-50 p-4">
      <div className="w-full max-w-lg bg-[#07070f] border border-[#1e1e3a] rounded-lg p-8
                      flex flex-col gap-6 shadow-2xl">

        {/* Header */}
        <div className="flex flex-col gap-2">
          <span className="text-4xl">{current.emoji}</span>
          <Steps current={step} total={STEPS.length} />
          <h1 className="text-xl font-bold text-white font-mono">{current.title}</h1>
          <p className="text-sm text-gray-500 font-mono">{current.subtitle}</p>
        </div>

        {/* Contenido del step */}
        <div className="flex flex-col gap-4">
          {current.render({ data, set })}
        </div>

        {/* Navegación */}
        <div className="flex items-center justify-between mt-2">
          <button
            type="button"
            onClick={() => setStep(s => s - 1)}
            disabled={step === 0}
            className="text-xs font-mono text-gray-600 hover:text-gray-400 disabled:opacity-0 transition-colors"
          >
            ← Atrás
          </button>
          <button
            type="button"
            onClick={handleNext}
            disabled={!canNext || saving}
            className="bg-[#4a90d9] hover:bg-[#3a80c9] disabled:bg-[#1a2a4a] disabled:cursor-not-allowed
                       text-white px-6 py-2 text-sm font-mono font-bold rounded transition-colors"
          >
            {saving ? 'Guardando...' : step === STEPS.length - 1 ? '¡Empezar! 🚀' : 'Siguiente →'}
          </button>
        </div>
      </div>
    </div>
  )
}
