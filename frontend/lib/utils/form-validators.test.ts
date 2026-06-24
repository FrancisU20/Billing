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

  it('validates Ecuadorian mobile numbers: 09 + 8 digits', () => {
    expect(isPhoneInput('0998630405')).toBe(true)
    expect(isPhoneInput('0999999999')).toBe(true)
    expect(isPhoneInput('+593 99 863 0405')).toBe(true)
    expect(isPhoneInput('099863040')).toBe(false) // 9 digitos, falta uno
    expect(isPhoneInput('09986304055')).toBe(false) // 11 digitos, sobra uno
    expect(isPhoneInput('0898630405')).toBe(false) // no empieza con 09
  })

  it('validates Ecuadorian landline numbers: area code 2-7 + 7 digits', () => {
    expect(isPhoneInput('062951377')).toBe(true)
    expect(isPhoneInput('+593 6 295 1377')).toBe(true)
    expect(isPhoneInput('012951377')).toBe(false) // codigo de area 1 no existe
    expect(isPhoneInput('08295137')).toBe(false) // codigo de area 8 no existe
    expect(isPhoneInput('06295137')).toBe(false) // 8 digitos, falta uno
    expect(isPhoneInput('0629513777')).toBe(false) // 10 digitos, sobra uno
  })

  it('rejects non-phone inputs', () => {
    expect(isPhoneInput('123')).toBe(false)
    expect(isPhoneInput('correo@ejemplo.com')).toBe(false)
  })

  it('validates basic email shape', () => {
    expect(isEmailInput('admin@empresa.com')).toBe(true)
    expect(isEmailInput('correo-malo')).toBe(false)
  })
})
