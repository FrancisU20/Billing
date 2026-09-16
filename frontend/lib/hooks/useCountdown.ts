import { useEffect, useState } from 'react'

function secondsUntil(expiresAt: string): number {
  return Math.max(0, Math.round((new Date(expiresAt).getTime() - Date.now()) / 1000))
}

/**
 * Returns seconds remaining until `expiresAt` (ISO string), ticking every second.
 * Returns 0 once expired or when `expiresAt` is falsy.
 */
export function useCountdown(expiresAt: string | null | undefined): number {
  const [secondsLeft, setSecondsLeft] = useState(() => (expiresAt ? secondsUntil(expiresAt) : 0))

  useEffect(() => {
    if (!expiresAt) {
      setSecondsLeft(0)
      return
    }
    setSecondsLeft(secondsUntil(expiresAt))
    const id = setInterval(() => {
      const s = secondsUntil(expiresAt)
      setSecondsLeft(s)
      if (s === 0) clearInterval(id)
    }, 1_000)
    return () => clearInterval(id)
  }, [expiresAt])

  return secondsLeft
}

export function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}
