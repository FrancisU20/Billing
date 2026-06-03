import { z } from "zod";

export type FieldErrors<T extends string> = Partial<Record<T, string>>;

/**
 * Parsea el valor de un <select> con el schema Zod correspondiente.
 * Lanza si el valor no es válido — evita casteos sin validación.
 */
export function parseSelectValue<T>(schema: z.ZodType<T>, value: string): T {
  return schema.parse(value);
}

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
