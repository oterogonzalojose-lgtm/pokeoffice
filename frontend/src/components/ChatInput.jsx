import { useState, useEffect, useRef } from 'react'

const SUGGESTIONS = [
  'Avisá a los clientes que hoy no tomamos más turnos',
  'Hacé un balance de este mes con $80.000 de ingresos y $35.000 de gastos',
  'Redactá un post de Instagram para promocionar un 20% de descuento',
  'Necesito una orden de compra para 50 unidades de producto X a $500 c/u',
]

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue]       = useState('')
  const [listening, setListening] = useState(false)
  const recognitionRef           = useRef(null)
  const spaceHeldRef             = useRef(false)

  // Init recognition once
  useEffect(() => {
    if (!SpeechRecognition) return
    const rec = new SpeechRecognition()
    rec.lang = 'es-AR'
    rec.continuous = false
    rec.interimResults = false

    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      setValue(prev => (prev ? prev + ' ' + transcript : transcript))
    }
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    recognitionRef.current = rec
  }, [])

  function startListening() {
    if (!recognitionRef.current || listening || disabled) return
    setListening(true)
    recognitionRef.current.start()
  }

  function stopListening() {
    if (!recognitionRef.current || !listening) return
    recognitionRef.current.stop()
  }

  // Spacebar hold — only when input is NOT focused
  useEffect(() => {
    function onKeyDown(e) {
      if (e.code !== 'Space') return
      if (document.activeElement?.tagName === 'INPUT') return
      if (spaceHeldRef.current) return
      e.preventDefault()
      spaceHeldRef.current = true
      startListening()
    }
    function onKeyUp(e) {
      if (e.code !== 'Space') return
      if (!spaceHeldRef.current) return
      spaceHeldRef.current = false
      stopListening()
    }
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup',   onKeyUp)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup',   onKeyUp)
    }
  }, [listening, disabled])

  function handleSubmit(e) {
    e.preventDefault()
    const msg = value.trim()
    if (!msg || disabled) return
    onSend(msg)
    setValue('')
  }

  const hasSpeech = !!SpeechRecognition

  return (
    <div className="flex flex-col gap-2">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          className="flex-1 bg-[#0d0d1f] border-2 border-[#4a4a8a] px-3 py-2 text-sm text-white
                     placeholder-gray-500 focus:outline-none focus:border-[#6a6acf]
                     font-mono disabled:opacity-50"
          placeholder="Escribí o hablá (mantené espacio)..."
          value={value}
          onChange={e => setValue(e.target.value)}
          disabled={disabled}
        />

        {/* Mic button */}
        {hasSpeech && (
          <button
            type="button"
            onMouseDown={startListening}
            onMouseUp={stopListening}
            onMouseLeave={stopListening}
            disabled={disabled}
            title="Mantené apretado para hablar"
            className={`px-3 py-2 border-2 text-lg transition-all
              ${listening
                ? 'bg-red-600 border-red-400 animate-pulse text-white'
                : 'bg-[#1a1a3e] border-[#4a4a8a] hover:border-[#6a6acf] text-gray-300 hover:text-white'}
              disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            🎙️
          </button>
        )}

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

      {/* Recording indicator */}
      {listening && (
        <div className="flex items-center gap-2 text-xs font-mono text-red-400 animate-pulse">
          <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
          Escuchando... soltá para terminar
        </div>
      )}

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
