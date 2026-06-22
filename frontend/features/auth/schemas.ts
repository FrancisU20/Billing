import { z } from 'zod'

export const loginSchema = z.object({
  username: z.string().min(1, 'El email es requerido').email('Email inválido'),
  password: z.string().min(1, 'La contraseña es requerida'),
})

export const newPasswordSchema = z
  .object({
    newPassword: z
      .string()
      .min(8, 'Mínimo 8 caracteres')
      .regex(/[A-Z]/, 'Debe incluir una mayúscula')
      .regex(/[0-9]/, 'Debe incluir un número'),
    confirmPassword: z.string().min(1, 'Confirma la contraseña'),
  })
  .refine((v) => v.newPassword === v.confirmPassword, {
    message: 'Las contraseñas no coinciden',
    path: ['confirmPassword'],
  })

export const forgotPasswordSchema = z.object({
  username: z.string().min(1, 'El email es requerido').email('Email inválido'),
})

export const resetPasswordSchema = z
  .object({
    confirmationCode: z.string().min(1, 'El código es requerido'),
    newPassword: z
      .string()
      .min(8, 'Mínimo 8 caracteres')
      .regex(/[A-Z]/, 'Debe incluir una mayúscula')
      .regex(/[0-9]/, 'Debe incluir un número'),
    confirmPassword: z.string().min(1, 'Confirma la contraseña'),
  })
  .refine((v) => v.newPassword === v.confirmPassword, {
    message: 'Las contraseñas no coinciden',
    path: ['confirmPassword'],
  })

export const authTokensResponseSchema = z.object({
  id_token: z.string().min(1),
  access_token: z.string().min(1),
  refresh_token: z.string().min(1),
})

export const authChallengeResponseSchema = z.object({
  challenge_name: z.string().min(1),
  session: z.string().min(1),
  parameters: z.record(z.string(), z.string()).optional().default({}),
})

export const loginResponseSchema = z.union([authChallengeResponseSchema, authTokensResponseSchema])

export const refreshResponseSchema = z.object({
  id_token: z.string().min(1),
  access_token: z.string().min(1),
})

export const forgotPasswordResponseSchema = z.object({
  message: z.string().min(1),
})

export type LoginFormValues = z.infer<typeof loginSchema>
export type NewPasswordFormValues = z.infer<typeof newPasswordSchema>
export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>
export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>
