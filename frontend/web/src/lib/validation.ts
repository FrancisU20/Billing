export type FieldErrors<T extends string> = Partial<Record<T, string>>;

export function required(value: string, label: string) {
  return value.trim() ? undefined : `${label} es obligatorio`;
}

export function exactDigits(value: string, digits: number, label: string) {
  return new RegExp(`^\\d{${digits}}$`).test(value)
    ? undefined
    : `${label} debe tener ${digits} dígitos`;
}

export function positiveNumber(value: number, label: string) {
  return Number.isFinite(value) && value > 0 ? undefined : `${label} debe ser mayor a cero`;
}

export function hasErrors<T extends string>(errors: FieldErrors<T>) {
  return Object.values(errors).some(Boolean);
}
