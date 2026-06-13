import { describe, expect, it } from 'vitest'
import { isValidCedula, isValidRuc } from './ruc'

describe('isValidRuc', () => {
  it('accepts a natural person / RIMPE RUC (cedula + 001)', () => {
    expect(isValidRuc('1710034065001')).toBe(true)
  })

  it('accepts a public entity RUC (third digit 6 + 0001)', () => {
    expect(isValidRuc('1760000070001')).toBe(true)
  })

  it('accepts a private company RUC (third digit 9 + 001)', () => {
    expect(isValidRuc('1792146739001')).toBe(true)
  })

  it('rejects a natural person RUC with an invalid establishment suffix', () => {
    expect(isValidRuc('1710034065002')).toBe(false)
  })

  it('rejects an invalid province code', () => {
    expect(isValidRuc('2592146739001')).toBe(false)
  })

  it('rejects values that are not 13 digits', () => {
    expect(isValidRuc('1710034065')).toBe(false)
    expect(isValidRuc('')).toBe(false)
  })
})

describe('isValidCedula', () => {
  it('accepts a valid cedula', () => {
    expect(isValidCedula('1710034065')).toBe(true)
  })

  it('rejects a cedula with an invalid check digit', () => {
    expect(isValidCedula('1710034066')).toBe(false)
  })
})
