export const DECIMAL_2_RE = /^\d+(\.\d{1,2})?$/
export const SIMPLE_EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Celular: siempre empieza con "09" y tiene exactamente 10 digitos, ej. 0998630405.
const ECUADOR_MOBILE_RE = /^09\d{8}$/
// Convencional: "0" + codigo de area + 7 digitos = 9 digitos en total, ej. 062951377.
// 2-7 son los unicos codigos de area vigentes en Ecuador (02 Pichincha ... 07 El Oro).
const ECUADOR_LANDLINE_RE = /^0[2-7]\d{7}$/

function normalizeEcuadorPhone(value: string): string {
  const digits = (value ?? '').trim().replace(/[\s-]/g, '')
  // +593 es el codigo de pais; el numero local sin el 0 inicial sigue despues.
  return digits.startsWith('+593') ? `0${digits.slice(4)}` : digits
}

export function isDecimalInput(value: string): boolean {
  return DECIMAL_2_RE.test(value.trim())
}

export function isPositiveDecimalInput(value: string): boolean {
  return isDecimalInput(value) && Number(value) > 0
}

export function isPercentageInput(value: string): boolean {
  if (!isDecimalInput(value)) return false
  const numeric = Number(value)
  return Number.isFinite(numeric) && numeric >= 0 && numeric <= 100
}

export function isPhoneInput(value: string): boolean {
  const digits = normalizeEcuadorPhone(value)
  return ECUADOR_MOBILE_RE.test(digits) || ECUADOR_LANDLINE_RE.test(digits)
}

export function isEmailInput(value: string): boolean {
  return SIMPLE_EMAIL_RE.test(value.trim())
}
