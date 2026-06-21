import { describe, expect, it } from 'vitest'
import { formatBillingPrice, isCustomQuotePlan } from './format'

const plan = { monthly_price: '9.99', annual_price: '99.00' }

describe('formatBillingPrice', () => {
  it('defaults to the monthly price', () => {
    const result = formatBillingPrice(plan)
    expect(result).toContain('9,99')
    expect(result).toContain('/ mes')
  })

  it('shows the annual price when billing cycle is year', () => {
    const result = formatBillingPrice(plan, 'year')
    expect(result).toContain('99,00')
    expect(result).toContain('/ año')
  })
})

describe('isCustomQuotePlan', () => {
  it('is true for plans without self-service checkout', () => {
    expect(isCustomQuotePlan({ self_service: false })).toBe(true)
  })

  it('is false for self-service plans', () => {
    expect(isCustomQuotePlan({ self_service: true })).toBe(false)
  })
})
