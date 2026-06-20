import { describe, expect, it } from 'vitest'
import {
  calendarDaysForMonth,
  monthRange,
  normalizeDateRange,
  selectDateInRange,
  validDateOnly,
  weekRange,
} from './date-range'

describe('date-range utils', () => {
  it('validates real date-only values', () => {
    expect(validDateOnly('2026-02-28')).toBe(true)
    expect(validDateOnly('2026-02-31')).toBe(false)
    expect(validDateOnly('2026/02/28')).toBe(false)
  })

  it('normalizes inverted ranges', () => {
    expect(normalizeDateRange({ from: '2026-06-20', to: '2026-06-01' })).toEqual({
      from: '2026-06-01',
      to: '2026-06-20',
    })
  })

  it('keeps selected ranges ordered', () => {
    expect(selectDateInRange({ from: '2026-06-20', to: '' }, '2026-06-10', 'to')).toEqual({
      from: '2026-06-10',
      to: '2026-06-20',
    })
  })

  it('builds Ecuador business presets as date-only ranges', () => {
    expect(weekRange('2026-06-17')).toEqual({ from: '2026-06-15', to: '2026-06-21' })
    expect(monthRange('2026-02-10')).toEqual({ from: '2026-02-01', to: '2026-02-28' })
  })

  it('returns a fixed six-week calendar grid', () => {
    const days = calendarDaysForMonth('2026-06-01')
    expect(days).toHaveLength(42)
    expect(days[0].iso).toBe('2026-06-01')
    expect(days[0].inCurrentMonth).toBe(true)
  })
})
