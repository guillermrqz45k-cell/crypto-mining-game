// Gráfico SVG propio (sin librerías externas): producción de HCK por día.
export default function ProductionChart({ data }) {
  const points = Array.isArray(data) ? data : []
  if (!points.length) return <p className="empty">Aún no hay datos de producción. Mina y recolecta para ver tu historial.</p>
  const values = points.map((p) => Number(p.hck ?? p.amount ?? p.value ?? 0) || 0)
  const labels = points.map((p) => p.date ?? p.day ?? '')
  const max = Math.max(...values, 1)
  const W = 640, H = 200, PAD = 28
  const stepX = points.length > 1 ? (W - PAD * 2) / (points.length - 1) : 0
  const xy = values.map((v, i) => [PAD + i * stepX, H - PAD - (v / max) * (H - PAD * 2)])
  const line = xy.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const area = `${line} L${xy[xy.length - 1][0].toFixed(1)},${H - PAD} L${xy[0][0].toFixed(1)},${H - PAD} Z`
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Gráfico de producción de HCK de los últimos días">
        <defs>
          <linearGradient id="prodFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#22d3ee" stopOpacity=".45" />
            <stop offset="100%" stopColor="#a78bfa" stopOpacity=".02" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75, 1].map((f) => (
          <line key={f} x1={PAD} x2={W - PAD} y1={H - PAD - f * (H - PAD * 2)} y2={H - PAD - f * (H - PAD * 2)} stroke="rgba(154,154,192,.18)" strokeDasharray="4 4" />
        ))}
        <path d={area} fill="url(#prodFill)" />
        <path d={line} fill="none" stroke="#22d3ee" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        {xy.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="3.5" fill="#a78bfa" stroke="#0a0a1a" strokeWidth="1.5">
            <title>{`${labels[i] || `Día ${i + 1}`}: ${values[i].toLocaleString('es')} HCK`}</title>
          </circle>
        ))}
        {labels.map((l, i) => (i % Math.ceil(labels.length / 7) === 0 ? (
          <text key={i} x={xy[i][0]} y={H - 8} fill="#9a9ac0" fontSize="10" textAnchor="middle">{String(l).slice(5) || l}</text>
        ) : null))}
        <text x={PAD} y={16} fill="#9a9ac0" fontSize="11">Máx. {max.toLocaleString('es')} HCK / día</text>
      </svg>
      <p className="small muted center">Total del periodo: <b className="cyan">{values.reduce((a, b) => a + b, 0).toLocaleString('es')} HCK</b></p>
    </div>
  )
}
