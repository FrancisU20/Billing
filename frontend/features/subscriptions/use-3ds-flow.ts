import { useCallback, useState } from 'react'
import { subscriptionsApi } from './api'

export type ThreeDsState =
  | { phase: 'idle' }
  | { phase: 'awaiting'; redirectUrl: string; orderId: string }
  | { phase: 'checking' }
  | { phase: 'failed'; error: string }

const _POLL_MAX = 10
const _POLL_DELAY_MS = 3000

async function _pollUntilPaid(orderId: string): Promise<'PAID' | 'FAILED' | 'TIMEOUT'> {
  for (let i = 0; i < _POLL_MAX; i++) {
    if (i > 0) await new Promise((r) => setTimeout(r, _POLL_DELAY_MS))
    const payment = await subscriptionsApi.getPayment(orderId)
    if (payment.status === 'PAID') return 'PAID'
    if (payment.status === 'FAILED' || payment.status === 'REJECTED') return 'FAILED'
  }
  return 'TIMEOUT'
}

export function use3dsFlow() {
  const [state, setState] = useState<ThreeDsState>({ phase: 'idle' })

  const startRedirect = useCallback((redirectUrl: string, orderId: string) => {
    setState({ phase: 'awaiting', redirectUrl, orderId })
    // Open 3DS page in a new tab to preserve app state.
    window.open(redirectUrl, '_blank', 'noopener,noreferrer')
  }, [])

  const checkStatus = useCallback(
    async (onPaid: (orderId: string) => Promise<void>) => {
      if (state.phase !== 'awaiting') return
      const { orderId } = state
      setState({ phase: 'checking' })
      try {
        const outcome = await _pollUntilPaid(orderId)
        if (outcome === 'PAID') {
          await onPaid(orderId)
          setState({ phase: 'idle' })
        } else {
          setState({
            phase: 'failed',
            error:
              outcome === 'TIMEOUT'
                ? 'No se pudo confirmar el pago. Intenta de nuevo o contacta soporte.'
                : 'El pago fue rechazado por el banco.',
          })
        }
      } catch {
        setState({ phase: 'failed', error: 'Error al verificar el estado del pago.' })
      }
    },
    [state],
  )

  const reset = useCallback(() => setState({ phase: 'idle' }), [])

  return { state, startRedirect, checkStatus, reset }
}
