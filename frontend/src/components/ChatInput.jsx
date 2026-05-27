import { useState } from 'react'

const SUGGESTIONS = [
  'Avisá a los clientes que hoy no tomamos más turnos',
  'Hacé un balance de este mes con $80.000 de ingresos y $35.000 de gastos',
  'Redactá un post de Instagram para promocionar un 20% de descuento',
  'Necesito una orden de compra para 50 unidades de producto X a $500 c/u',
]

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    const msg = value.trim()
    if (!msg || disabled) return
    onSend(msg)
    setValue('')
  }

  return (
    <div className="flex flex-col gap-2">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          className="flex-1 bg-[#0d0d1f] border-2 border-[#4a4a8a] px-3 py-2 text-sm text-white
                     placeholder-gray-500 focus:outline-none focus:border-[#6a6acf]
                     font-mono disabled:opacity-50"
          placeholder="Escribí una instrucción para tu equipo..."
          value={value}
          onChange={e => setValue(e.target.value)}
          disabled={disabled}
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="bg-[#4a90d9] hover:bg-[#3a80c9] disabled:bg-[#2a3a5a] disabled:cursor-not-allowed
                     text-white px-4 py-2 text-sm font-mono border-2 border-[#2a70b9]
                     transition-colors"
        >
          {disabled ? '...' : 'Enviar'}
        </button>
      </form>

      <div className="flex flex-wrap gap-1">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => !disabled && onSend(s)}
            disabled={disabled}
            className="text-xs bg-[#1a1a3e] border border-[#3a3a7a] text-gray-400
                       hover:text-white hover:border-[#6a6acf] px-2 py-1 transition-colors
                       disabled:opacity-40 disabled:cursor-not-allowed font-mono text-left"
          >
            {s.slice(0, 40)}...
          </button>
        ))}
      </div>
    </div>
  )
}
