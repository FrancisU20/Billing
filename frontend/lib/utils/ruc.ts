function isValidProvinceCode(value: string): boolean {
  if (!/^\d{2}$/.test(value)) return false
  const province = Number(value)
  return province >= 1 && province <= 24
}

function modulo10(base: string, checkDigit: string): boolean {
  if (!/^\d{9}$/.test(base) || !/^\d$/.test(checkDigit)) return false
  const coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
  const total = base
    .split('')
    .map((digit, i) => Number(digit) * coef[i])
    .reduce((sum, v) => sum + (v >= 10 ? v - 9 : v), 0)
  const expected = total % 10 === 0 ? 0 : 10 - (total % 10)
  return expected === Number(checkDigit)
}

function modulo11Public(base: string, checkDigit: string): boolean {
  if (!/^\d{8}$/.test(base) || !/^\d$/.test(checkDigit)) return false
  const coef = [3, 2, 7, 6, 5, 4, 3, 2]
  const total = base.split('').reduce((sum, digit, i) => sum + Number(digit) * coef[i], 0)
  const remainder = total % 11
  const expected = remainder === 0 ? 0 : 11 - remainder
  return expected === Number(checkDigit)
}

function modulo11Legal(base: string, checkDigit: string): boolean {
  if (!/^\d{9}$/.test(base) || !/^\d$/.test(checkDigit)) return false
  const coef = [4, 3, 2, 7, 6, 5, 4, 3, 2]
  const total = base.split('').reduce((sum, digit, i) => sum + Number(digit) * coef[i], 0)
  const remainder = total % 11
  const expected = remainder === 0 ? 0 : 11 - remainder
  return expected === Number(checkDigit)
}

export function isValidCedula(value: string): boolean {
  const v = (value ?? '').trim()
  if (!/^\d{10}$/.test(v)) return false
  if (!isValidProvinceCode(v.slice(0, 2))) return false
  if (Number(v[2]) >= 6) return false
  return modulo10(v.slice(0, 9), v[9])
}

/**
 * Replica backend/shared/domain/value_objects/ecuador_identification.py::is_valid_ruc
 * para validación client-side: cédula+RIMPE (3er digito < 6), entidad pública (== 6) y
 * sociedad privada (== 9).
 */
export function isValidRuc(value: string): boolean {
  const v = (value ?? '').trim()
  if (!/^\d{13}$/.test(v)) return false
  if (!isValidProvinceCode(v.slice(0, 2))) return false

  const thirdDigit = Number(v[2])
  if (thirdDigit < 6) return isValidCedula(v.slice(0, 10)) && v.slice(10) === '001'
  if (thirdDigit === 6) return modulo11Public(v.slice(0, 8), v[8]) && v.slice(9) === '0001'
  if (thirdDigit === 9) return modulo11Legal(v.slice(0, 9), v[9]) && v.slice(10) === '001'
  return false
}
