/**
 * Mensajes de validación Zod centralizados.
 * Todos los schemas de formulario deben importar desde aquí
 * en lugar de hardcodear strings.
 */
export const vm = {
  emailInvalid: 'Email inválido',
  phoneInvalid: 'Teléfono inválido',
  rucInvalid: 'RUC ecuatoriano inválido',
  cedulaInvalid: 'Cédula ecuatoriana inválida',

  passwordMin: 'Mínimo 8 caracteres',
  passwordNeedsUppercase: 'Debe incluir una mayúscula',
  passwordNeedsNumber: 'Debe incluir un número',
  passwordsNoMatch: 'Las contraseñas no coinciden',
  passwordConfirmRequired: 'Confirma la contraseña',

  min: (n: number) => `Mínimo ${n} caracteres`,
  max: (n: number) => `Máximo ${n} caracteres`,
  maxItems: (n: number, label: string) => `Máximo ${n} ${label}`,
}
