import { describe, expect, it } from 'vitest'
import { formatDate, formatDateTime } from './format'

describe('formatDate', () => {
  it('formats date-only values as civil dates without UTC shifting', () => {
    expect(formatDate('2026-06-18')).toContain('18')
  })

  it('formats timestamps in Ecuador timezone', () => {
    expect(formatDateTime('2026-06-19T00:04:00.000Z')).toContain('19:04')
    expect(formatDateTime('2026-06-19T00:04:00.000Z')).toContain('18')
  })
})
