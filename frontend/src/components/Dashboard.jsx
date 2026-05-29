import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/api'

function KPI({ label, value, sub, color = '#4A90D9', icon }) {
  return (
    <div className="bg-[#0a0a18] border border-[#1e1e3a] rounded p-3 flex flex-col gap-1">
      <div className="flex items-center gap-1.5">
        {icon && <span className="text-base">{icon}</span>}
        <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-xl font-bold font-mono" style={{ color }}>{value}</p>
      {sub && <p className="text-[10px] font-mono text-gray-600">{sub}</p>}
    </div>
  )
}

function BarComparison({ ingresos, egresos }) {
  const max   = Math.max(ingresos, egresos, 1)
  const pctI  = (ingresos / max) * 100
  const pctE  = (egresos  / max) * 100
  const neto  = ingresos - egresos
  const pos   = neto >= 0

  return (
    <div className="bg-[#0a0a18] border border-[#1e1e3a] rounded p-3">
      <p className="text-[10px] font-mono text-gray-500 uppercase tracking-wide mb-2">
        Ingresos vs Egresos — Mes actual
      </p>
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-green-400 w-16 shrink-0">Ingresos</span>
          <div className="flex-1 bg-[#0d1f0d] rounded-sm h-4 relative overflow-hidden">
            <div
              className="absolute left-0 top-0 h-full bg-green-600 rounded-sm transition-all duration-700"
              style={{ width: `${pctI}%` }}
            />
            <span className="absolute right-1 top-0 h-full flex items-center text-[9px] font-mono text-green-300">
              ${ingresos.toLocaleString('es-AR')}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-red-400 w-16 shrink-0">Egresos</span>
          <div className="flex-1 bg-[#1f0d0d] rounded-sm h-4 relative overflow-hidden">
            <div
              className="absolute left-0 top-0 h-full bg-red-700 rounded-sm transition-all duration-700"
              style={{ width: `${pctE}%` }}
            />
            <span className="absolute right-1 top-0 h-full flex items-center text-[9px] font-mono text-red-300">
              ${egresos.toLocaleString('es-AR')}
            </span>
          </div>
        </div>
        <div className={`flex items-center justify-between mt-1 pt-1.5 border-t border-[#1e1e3a]`}>
          <span className="text-[10px] font-mono text-gray-500">Resultado neto</span>
          <span className={`text-sm font-bold font-mono ${pos ? 'text-green-400' : 'text-red-400'}`}>
            {pos ? '+' : ''}${neto.toLocaleString('es-AR')}
          </span>
        </div>
      </div>
    </div>
  )
}

function StockAlerts({ items }) {
  if (!items.length) return (
    <div className="bg-[#0a0a18] border border-[#1e1e3a] rounded p-3">
      <p className="text-[10px] font-mono text-gray-500 uppercase tracking-wide mb-2">⚠️ Stock bajo</p>
      <p className="text-[11px] font-mono text-green-500 italic">Todos los productos con stock OK ✓</p>
    </div>
  )

  return (
    <div className="bg-[#0a0a18] border border-[#2a1a0a] rounded p-3">
      <p className="text-[10px] font-mono text-orange-400 uppercase tracking-wide mb-2">
        ⚠️ Stock bajo — {items.length} producto{items.length > 1 ? 's' : ''}
      </p>
      <div className="flex flex-col gap-1">
        {items.slice(0, 5).map((p, i) => (
          <div key={i} className="flex items-center justify-between gap-2">
            <span className="text-[10px] font-mono text-gray-300 truncate flex-1">
              {p.descripcion || p.codigo}
            </span>
            <span className="text-[10px] font-mono text-orange-400 shrink-0">
              {p.unidades} u. (mín {p.stock_minimo})
            </span>
          </div>
        ))}
        {items.length > 5 && (
          <p className="text-[9px] font-mono text-gray-600 mt-1">
            +{items.length - 5} más…
          </p>
        )}
      </div>
    </div>
  )
}

function MovimientosRecientes({ movimientos }) {
  if (!movimientos.length) return (
    <div className="bg-[#0a0a18] border border-[#1e1e3a] rounded p-3">
      <p className="text-[10px] font-mono text-gray-500 uppercase tracking-wide mb-2">Movimientos recientes</p>
      <p className="text-[11px] font-mono text-gray-600 italic">Sin movimientos aún.</p>
    </div>
  )

  return (
    <div className="bg-[#0a0a18] border border-[#1e1e3a] rounded p-3">
      <p className="text-[10px] font-mono text-gray-500 uppercase tracking-wide mb-2">
        Movimientos recientes
      </p>
      <div className="flex flex-col gap-1">
        {movimientos.slice(0, 8).map((m, i) => {
          const esIngreso = m.ingreso && String(m.ingreso).trim() !== ""
          const monto = esIngreso ? m.ingreso : m.egreso
          return (
            <div key={i} className="flex items-center gap-2 py-0.5 border-b border-[#14142a] last:border-0">
              <span className="text-[9px] font-mono text-gray-600 w-16 shrink-0">{m.fecha}</span>
              <span className="text-[10px] font-mono text-gray-300 flex-1 truncate">{m.descripcion}</span>
              <span className={`text-[10px] font-mono font-bold shrink-0 ${esIngreso ? 'text-green-400' : 'text-red-400'}`}>
                {esIngreso ? '+' : '-'}${Number(monto).toLocaleString('es-AR')}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function CuentasPorBanco({ cuentas }) {
  const items = Object.entries(cuentas).filter(([, v]) => v > 0)
  if (!items.length) return null

  const total = items.reduce((s, [, v]) => s + v, 0)
  const labels = {
    efectivo: '💵 Efectivo',
    banco_cte: '🏦 Banco cte.',
    banco_ahorro: '🏦 Cja. ahorro',
    mercado_pago: '📱 Mercado Pago',
    otros: '💼 Otros',
  }

  return (
    <div className="bg-[#0a0a18] border border-[#1e1e3a] rounded p-3">
      <p className="text-[10px] font-mono text-gray-500 uppercase tracking-wide mb-2">Distribución de liquidez</p>
      <div className="flex flex-col gap-1">
        {items.map(([key, val]) => (
          <div key={key} className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-gray-400 w-28 shrink-0">
              {labels[key] || key}
            </span>
            <div className="flex-1 bg-[#0d0d1f] rounded-sm h-2.5 relative overflow-hidden">
              <div
                className="absolute left-0 top-0 h-full bg-blue-700 rounded-sm"
                style={{ width: `${(val / total) * 100}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-blue-300 w-20 text-right shrink-0">
              ${val.toLocaleString('es-AR')}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await apiFetch('/dashboard')
      const json = await res.json()
      if (json.error) throw new Error(json.error)
      setData(json)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  if (loading) return (
    <div className="flex-1 flex items-center justify-center">
      <p className="text-sm font-mono text-gray-500 animate-pulse">Cargando dashboard…</p>
    </div>
  )

  if (error) return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3 p-4 text-center">
      <span className="text-3xl">📊</span>
      <p className="text-sm font-mono text-gray-400">
        El dashboard estará disponible una vez que tu planilla maestra esté configurada.
      </p>
      <p className="text-[10px] font-mono text-gray-600">
        El equipo de Pokeoffice te ayudará a configurarla.
      </p>
      <button onClick={fetchData}
        className="text-xs font-mono text-blue-400 hover:text-blue-300 border border-blue-900 px-3 py-1 rounded mt-1">
        Reintentar
      </button>
    </div>
  )

  const fin  = data?.finanzas   ?? {}
  const movs = data?.movimientos ?? []
  const bajo = data?.stock_bajo  ?? []

  return (
    <div className="flex-1 flex flex-col gap-3 overflow-y-auto pr-1 pb-2"
         style={{ scrollbarWidth: 'thin' }}>

      {/* Actualizar */}
      <div className="flex items-center justify-between shrink-0">
        <p className="text-[9px] font-mono text-gray-600">
          Actualizado: {data?.generado_el}
        </p>
        <button onClick={fetchData}
          className="text-[9px] font-mono text-blue-400 hover:text-blue-300 transition-colors">
          ↻ Actualizar
        </button>
      </div>

      {/* KPIs principales */}
      <div className="grid grid-cols-2 gap-2 shrink-0">
        <KPI
          icon="💰"
          label="Total liquidez"
          value={`$${(fin.total_liquidez ?? 0).toLocaleString('es-AR')}`}
          color="#4A90D9"
        />
        <KPI
          icon={fin.resultado_neto >= 0 ? '📈' : '📉'}
          label="Resultado neto"
          value={`${fin.resultado_neto >= 0 ? '+' : ''}$${(fin.resultado_neto ?? 0).toLocaleString('es-AR')}`}
          color={fin.resultado_neto >= 0 ? '#27AE60' : '#E74C3C'}
          sub="del mes"
        />
      </div>

      {/* Barras ingresos vs egresos */}
      <div className="shrink-0">
        <BarComparison
          ingresos={fin.ingresos_mes ?? 0}
          egresos={fin.egresos_mes   ?? 0}
        />
      </div>

      {/* Distribución por cuenta */}
      {fin.cuentas && (
        <div className="shrink-0">
          <CuentasPorBanco cuentas={fin.cuentas} />
        </div>
      )}

      {/* Alertas stock */}
      <div className="shrink-0">
        <StockAlerts items={bajo} />
      </div>

      {/* Movimientos recientes */}
      <div className="shrink-0">
        <MovimientosRecientes movimientos={movs} />
      </div>
    </div>
  )
}
