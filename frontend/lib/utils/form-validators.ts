export const DECIMAL_2_RE = /^\d+(\.\d{1,2})?$/
export const ECUADOR_PHONE_RE = /^\+?[0-9][0-9\s-]{6,19}$/
export const SIMPLE_EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

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
  return ECUADOR_PHONE_RE.test(value.trim())
}

export function isEmailInput(value: string): boolean {
  return SIMPLE_EMAIL_RE.test(value.trim())
}
