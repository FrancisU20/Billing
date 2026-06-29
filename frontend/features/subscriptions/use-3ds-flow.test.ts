// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { subscriptionsApi } from './api'
import type { PaymentStatus } from './schemas'
import { use3dsFlow } from './use-3ds-flow'

vi.mock('./api', () => ({
  subscriptionsApi: {
    getPayment: vi.fn(),
  },
}))

describe('use3dsFlow', () => {
  beforeEach(() => {
    vi.spyOn(window, 'open').mockImplementation(() => null)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('does not complete activation when a PAID poll resolves after unmount', async () => {
    let resolvePayment: (value: PaymentStatus) => void = () => {}
    vi.mocked(subscriptionsApi.getPayment).mockReturnValue(
      new Promise((resolve) => {
        resolvePayment = resolve
      }),
    )
    const onPaid = vi.fn().mockResolvedValue(undefined)
    const { result, unmount } = renderHook(() => use3dsFlow())

    act(() => {
      result.current.startRedirect('https://bank.test/3ds', 'DP-1', 'mct_tok')
    })

    const check = act(async () => {
      const pending = result.current.checkStatus(onPaid)
      unmount()
      resolvePayment(_paymentStatus('PAID'))
      await pending
    })

    await check

    expect(onPaid).not.toHaveBeenCalled()
  })

  it('ignores the active poll when reset is called before the response resolves', async () => {
    let resolvePayment: (value: PaymentStatus) => void = () => {}
    vi.mocked(subscriptionsApi.getPayment).mockReturnValue(
      new Promise((resolve) => {
        resolvePayment = resolve
      }),
    )
    const onPaid = vi.fn().mockResolvedValue(undefined)
    const { result } = renderHook(() => use3dsFlow())

    act(() => {
      result.current.startRedirect('https://bank.test/3ds', 'DP-1', 'mct_tok')
    })

    const pending = act(async () => {
      const check = result.current.checkStatus(onPaid)
      result.current.reset()
      resolvePayment(_paymentStatus('PAID'))
      await check
    })

    await pending

    await waitFor(() => expect(result.current.state.phase).toBe('idle'))
    expect(onPaid).not.toHaveBeenCalled()
  })
})

function _paymentStatus(status: string): PaymentStatus {
  return {
    order_id: 'DP-1',
    status,
    plan_id: 'plan-1',
    amount: '5.99',
    currency: 'USD',
    tenant_id: null,
    plan_cycle: 'month',
    created_at: '2026-06-28T00:00:00Z',
    confirmed_at: null,
  }
}
