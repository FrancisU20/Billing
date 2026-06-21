import { describe, expect, it } from 'vitest'
import { formatDate, formatDateTime, formatRelativeTime } from './format'

describe('formatDate', () => {
  it('formats date-only values as civil dates without UTC shifting', () => {
    expect(formatDate('2026-06-18')).toContain('18')
  })

  it('formats timestamps in Ecuador timezone', () => {
    expect(formatDateTime('2026-06-19T00:04:00.000Z')).toContain('19:04')
    expect(formatDateTime('2026-06-19T00:04:00.000Z')).toContain('18')
  })
})

describe('formatRelativeTime', () => {
  const now = new Date('2026-06-20T12:00:00.000Z')

  it('returns minutes for very recent timestamps', () => {
    expect(formatRelativeTime('2026-06-20T11:50:00.000Z', now)).toBe('Hace 10 min')
  })

  it('returns hours within the same day', () => {
    expect(formatRelativeTime('2026-06-20T09:00:00.000Z', now)).toBe('Hace 3 h')
  })

  it('returns "Ayer" for exactly one day ago', () => {
    expect(formatRelativeTime('2026-06-19T12:00:00.000Z', now)).toBe('Ayer')
  })

  it('returns days for less than a month ago', () => {
    expect(formatRelativeTime('2026-06-15T12:00:00.000Z', now)).toBe('Hace 5 días')
  })

  it('returns months for less than a year ago', () => {
    expect(formatRelativeTime('2026-04-20T12:00:00.000Z', now)).toBe('Hace 2 meses')
  })
})
