import { describe, expect, it } from 'vitest'
import {
  isDecimalInput,
  isEmailInput,
  isPercentageInput,
  isPhoneInput,
  isPositiveDecimalInput,
} from './form-validators'

describe('form validators', () => {
  it('validates money-like decimal inputs with up to two decimals', () => {
    expect(isDecimalInput('10')).toBe(true)
    expect(isDecimalInput('10.25')).toBe(true)
    expect(isDecimalInput('10.255')).toBe(false)
    expect(isDecimalInput('-1')).toBe(false)
    expect(isPositiveDecimalInput('0')).toBe(false)
    expect(isPositiveDecimalInput('0.01')).toBe(true)
  })

  it('validates percentage bounds', () => {
    expect(isPercentageInput('0')).toBe(true)
    expect(isPercentageInput('100')).toBe(true)
    expect(isPercentageInput('100.01')).toBe(false)
    expect(isPercentageInput('abc')).toBe(false)
  })

  it('validates practical Ecuadorian phone inputs', () => {
    expect(isPhoneInput('0999999999')).toBe(true)
    expect(isPhoneInput('+593 99 999 9999')).toBe(true)
    expect(isPhoneInput('123')).toBe(false)
    expect(isPhoneInput('correo@ejemplo.com')).toBe(false)
  })

  it('validates basic email shape', () => {
    expect(isEmailInput('admin@empresa.com')).toBe(true)
    expect(isEmailInput('correo-malo')).toBe(false)
  })
})
