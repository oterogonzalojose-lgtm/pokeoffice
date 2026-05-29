import { useState } from 'react'

import { apiFetch } from '../utils/api'

const TIPOS_NEGOCIO = [
  'Consultorio / Salud', 'Tienda / Retail', 'Estudio profesional',
  'Gastronomía', 'Servicios / Reparaciones', 'Educación / Clases',
  'Belleza / Estética', 'Tecnología', 'Otro',
]

const MONEDAS = [
  { code: 'ARS', label: '$ Peso argentino' },
  { code: 'USD', label: '$ Dólar estadounidense' },
  { code: 'EUR', label: '€ Euro' },
]

function Steps({ current, total }) {
  return (
    <div className="flex items-center gap-1.5 mb-8">
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full transition-all
            ${i < current ? 'bg-green-500' : i === current ? 'bg-blue-400' : 'bg-[#2a2a4a]'}`} />
          {i < total - 1 && (
            <div className={`h-px w-8 transition-all ${i < current ? 'bg-green-500' : 'bg-[#2a2a4a]'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

function Field({ label, value, onChange, placeholder, hint }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-mono text-gray-400">{label}</label>
      <input
        value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="bg-[#0a0a18] border border-[#2a2a4a] focus:border-[#4a4a9a] outline-none
                   px-3 py-2 text-sm text-white font-mono placeholder-gray-600 rounded transition-colors"
      />
      {hint && <p className="text-[10px] font-mono text-gray-600">{hint}</p>}
    </div>
  )
}

function OptionGrid({ options, value, onChange, columns = 3 }) {
  return (
    <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
      {options.map(opt => {
        const key = typeof opt === 'string' ? opt : opt.code
        const label = typeof opt === 'string' ? opt : opt.label
        return (
          <button key={key} type="button" onClick={() => onChange(key)}
            className={`text-xs font-mono px-3 py-2 rounded border text-left transition-all
              ${value === key
                ? 'border-blue-500 bg-[#0d1f3a] text-blue-300'
                : 'border-[#2a2a4a] bg-[#07070f] text-gray-400 hover:border-[#3a3a6a] hover:text-gray-200'}`}>
            {label}
          </button>
        )
      })}
    </div>
  )
}

const STEPS = [
  {
    title: 'Bienvenido a Pokeoffice',
    subtitle: 'Tu mini oficina con IA. En 3 pasos configuramos tu equipo.',
    emoji: '🏢',
    render: ({ data, set }) => (
      <div className="flex flex-col gap-4">
        <Field label="¿Cuál es tu nombre?" value={data.nombre_jefe}
          onChange={v => set('nombre_jefe', v)} placeholder="Ej: Martín, Ana..."
          hint="Así te llamará el VP al responder" />
        <Field label="Nombre de tu negocio" value={data.nombre_negocio}
          onChange={v => set('nombre_negocio', v)}
          placeholder="Ej: Consultorio Spinelli, Tienda La Paloma..." />
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
          <OptionGrid options={TIPOS_NEGOCIO} value={data.tipo_negocio}
            onChange={v => set('tipo_negocio', v)} columns={3} />
        </div>
        <Field label="Contanos brevemente qué hacés (opcional)" value={data.descripcion}
          onChange={v => set('descripcion', v)}
          placeholder="Ej: Clínica veterinaria especializada en mascotas pequeñas..."
          hint="Más contexto = respuestas más precisas de los agentes" />
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
          <OptionGrid options={MONEDAS} value={data.moneda}
            onChange={v => set('moneda', v)} columns={3} />
        </div>
        <div className="bg-[#0a0a18] border border-[#1e1e3a] rounded p-3 flex flex-col gap-1.5">
          <p className="text-[10px] font-mono text-gray-500 uppercase tracking-wide">Resumen</p>
          {[['Jefe', data.nombre_jefe], ['Negocio', data.nombre_negocio],
            ['Tipo', data.tipo_negocio], ['Moneda', data.moneda]].map(([k, v]) => (
            <p key={k} className="text-sm font-mono text-white">
              <span className="text-gray-500">{k}: </span>{v}
            </p>
          ))}
        </div>
      </div>
    ),
    valid: () => true,
  },
]

// ── Pantalla de creación de planilla ──────────────────────────────────────────

function CreatingScreen() {
  return (
    <div className="flex flex-col items-center gap-6 py-4">
      <div className="text-5xl animate-bounce">📊</div>
      <div className="flex flex-col items-center gap-2">
        <p className="text-white font-mono font-bold text-lg">Creando tu equipo...</p>
        <p className="text-gray-500 font-mono text-sm text-center">
          Estamos armando tu planilla maestra en Google Sheets.<br />Esto tarda unos segundos.
        </p>
      </div>
      <div className="flex gap-1">
        {[0, 1, 2].map(i => (
          <div key={i} className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"
            style={{ animationDelay: `${i * 0.2}s` }} />
        ))}
      </div>
    </div>
  )
}

// ── Pantalla de éxito ─────────────────────────────────────────────────────────

function DoneScreen({ nombreNegocio, planillaUrl, onEnter }) {
  return (
    <div className="flex flex-col items-center gap-6 py-2">
      <div className="text-5xl">🎉</div>
      <div className="flex flex-col items-center gap-2 text-center">
        <p className="text-white font-mono font-bold text-lg">¡Todo listo, {nombreNegocio}!</p>
        <p className="text-gray-500 font-mono text-sm">Tu equipo de agentes está configurado y listo para trabajar.</p>
      </div>

      {planillaUrl ? (
        <a href={planillaUrl} target="_blank" rel="noreferrer"
          className="flex items-center gap-2.5 bg-[#0f9d58] hover:bg-[#0d8f50] transition-colors
                     text-white font-mono text-sm px-4 py-2.5 rounded-lg">
          <SheetsIcon size={20} />
          <span>Ver tu planilla maestra →</span>
        </a>
      ) : (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-3 text-center">
          <p className="text-yellow-400 font-mono text-xs">
            ⚠️ La planilla se configurará cuando el administrador active la integración con Google Sheets.
          </p>
        </div>
      )}

      <button onClick={onEnter}
        className="bg-[#4a90d9] hover:bg-[#3a80c9] text-white px-8 py-2.5
                   text-sm font-mono font-bold rounded transition-colors mt-2">
        Entrar a mi oficina 🚀
      </button>
    </div>
  )
}

// ── Google Sheets icon ────────────────────────────────────────────────────────

export function SheetsIcon({ size = 24 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect width="24" height="24" rx="3" fill="#0F9D58" />
      <rect x="5.5" y="7" width="13" height="1.5" rx="0.5" fill="white" opacity="0.95" />
      <rect x="5.5" y="11" width="13" height="1.5" rx="0.5" fill="white" opacity="0.95" />
      <rect x="5.5" y="15" width="13" height="1.5" rx="0.5" fill="white" opacity="0.95" />
      <rect x="9.5" y="7" width="1.5" height="9.5" rx="0.5" fill="white" opacity="0.95" />
    </svg>
  )
}

// ── Componente principal ──────────────────────────────────────────────────────

export default function Onboarding({ onComplete }) {
  const [step,        setStep]        = useState(0)
  const [phase,       setPhase]       = useState('wizard')   // 'wizard' | 'creating' | 'done'
  const [planillaUrl, setPlanillaUrl] = useState(null)
  const [data, setData] = useState({
    nombre_jefe: '', nombre_negocio: '', tipo_negocio: '', descripcion: '', moneda: 'ARS',
  })

  function set(key, value) { setData(prev => ({ ...prev, [key]: value })) }

  async function handleNext() {
    if (step < STEPS.length - 1) { setStep(s => s + 1); return }

    // Último paso → guardar config + crear planilla
    setPhase('creating')

    try {
      await apiFetch('/config/onboarding', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    } catch { /* continuar aunque falle */ }

    try {
      const res  = await apiFetch('/planilla/setup', {
        method: 'POST',
        body: JSON.stringify({ nombre_negocio: data.nombre_negocio }),
      })
      const json = await res.json()
      if (json.ok && json.url) setPlanillaUrl(json.url)
    } catch { /* Google no configurado — continuar igual */ }

    setPhase('done')
  }

  if (phase === 'creating') {
    return (
      <div className="fixed inset-0 bg-[#04040e] flex items-center justify-center z-50 p-4">
        <div className="w-full max-w-lg bg-[#07070f] border border-[#1e1e3a] rounded-lg p-8 shadow-2xl">
          <CreatingScreen />
        </div>
      </div>
    )
  }

  if (phase === 'done') {
    return (
      <div className="fixed inset-0 bg-[#04040e] flex items-center justify-center z-50 p-4">
        <div className="w-full max-w-lg bg-[#07070f] border border-[#1e1e3a] rounded-lg p-8 shadow-2xl">
          <DoneScreen
            nombreNegocio={data.nombre_negocio}
            planillaUrl={planillaUrl}
            onEnter={() => onComplete({ ...data, planillaUrl })}
          />
        </div>
      </div>
    )
  }

  const current = STEPS[step]

  return (
    <div className="fixed inset-0 bg-[#04040e] flex items-center justify-center z-50 p-4">
      <div className="w-full max-w-lg bg-[#07070f] border border-[#1e1e3a] rounded-lg p-8 flex flex-col gap-6 shadow-2xl">
        <div className="flex flex-col gap-2">
          <span className="text-4xl">{current.emoji}</span>
          <Steps current={step} total={STEPS.length} />
          <h1 className="text-xl font-bold text-white font-mono">{current.title}</h1>
          <p className="text-sm text-gray-500 font-mono">{current.subtitle}</p>
        </div>
        <div className="flex flex-col gap-4">{current.render({ data, set })}</div>
        <div className="flex items-center justify-between mt-2">
          <button type="button" onClick={() => setStep(s => s - 1)} disabled={step === 0}
            className="text-xs font-mono text-gray-600 hover:text-gray-400 disabled:opacity-0 transition-colors">
            ← Atrás
          </button>
          <button type="button" onClick={handleNext} disabled={!current.valid(data)}
            className="bg-[#4a90d9] hover:bg-[#3a80c9] disabled:bg-[#1a2a4a] disabled:cursor-not-allowed
                       text-white px-6 py-2 text-sm font-mono font-bold rounded transition-colors">
            {step === STEPS.length - 1 ? '¡Empezar! 🚀' : 'Siguiente →'}
          </button>
        </div>
      </div>
    </div>
  )
}
