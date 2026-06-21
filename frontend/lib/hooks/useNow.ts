import { useEffect, useState } from 'react'

const TICK_MS = 30_000

/** Reloj en vivo (se refresca cada 30s) para mostrar fecha/hora actual en pantalla. */
export function useNow(): Date {
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), TICK_MS)
    return () => clearInterval(id)
  }, [])

  return now
}
