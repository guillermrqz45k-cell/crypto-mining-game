// Confeti simple en CSS (sin librerías). Se muestra unos segundos al subir de nivel.
import { useEffect, useState } from 'react'

const COLORS = ['#22d3ee', '#a78bfa', '#fbbf24', '#34d399', '#f87171', '#fb923c']

export default function Confetti({ show }) {
  const [pieces, setPieces] = useState([])
  useEffect(() => {
    if (!show) return
    const arr = Array.from({ length: 60 }, (_, i) => ({
      id: i, left: Math.random() * 100, delay: Math.random() * 0.8,
      color: COLORS[i % COLORS.length], rotate: Math.random() * 360,
    }))
    setPieces(arr)
    const t = setTimeout(() => setPieces([]), 3000)
    return () => clearTimeout(t)
  }, [show])
  if (!pieces.length) return null
  return (
    <div className="confetti" aria-hidden="true">
      {pieces.map((p) => (
        <i key={p.id} style={{ left: `${p.left}%`, background: p.color, animationDelay: `${p.delay}s`, transform: `rotate(${p.rotate}deg)` }} />
      ))}
    </div>
  )
}
