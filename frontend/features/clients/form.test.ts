import { describe, expect, it } from 'vitest'
import { derivePersonType } from './form'

describe('derivePersonType', () => {
  it('cedula is always natural, regardless of what was requested', () => {
    expect(derivePersonType('cedula', '1710034065', 'juridica')).toBe('natural')
  })

  it('RUC with third digit under 6 is natural', () => {
    expect(derivePersonType('ruc', '1710034065001', 'juridica')).toBe('natural')
  })

  it('RUC with third digit 9 is juridica', () => {
    expect(derivePersonType('ruc', '1792146739001', 'natural')).toBe('juridica')
  })

  it('RUC with third digit 6 (entidad publica) is juridica', () => {
    expect(derivePersonType('ruc', '1760013210001', 'natural')).toBe('juridica')
  })

  it('falls back to the requested value while the RUC is still incomplete', () => {
    expect(derivePersonType('ruc', '17', 'juridica')).toBe('juridica')
  })

  it('respects the manual choice for pasaporte and exterior', () => {
    expect(derivePersonType('pasaporte', 'A12345678', 'natural')).toBe('natural')
    expect(derivePersonType('exterior', 'TAX-998877', 'juridica')).toBe('juridica')
  })
})
