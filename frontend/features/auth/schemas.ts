import { z } from 'zod'
import { vm } from '@/lib/utils/validation-messages'

const passwordField = z
  .string()
  .min(8, vm.passwordMin)
  .regex(/[A-Z]/, vm.passwordNeedsUppercase)
  .regex(/[0-9]/, vm.passwordNeedsNumber)

export const loginSchema = z.object({
  username: z.string().min(1, 'El email es requerido').email(vm.emailInvalid),
  password: z.string().min(1, 'La contraseña es requerida'),
})

export const newPasswordSchema = z
  .object({
    newPassword: passwordField,
    confirmPassword: z.string().min(1, vm.passwordConfirmRequired),
  })
  .refine((v) => v.newPassword === v.confirmPassword, {
    message: vm.passwordsNoMatch,
    path: ['confirmPassword'],
  })

export const forgotPasswordSchema = z.object({
  username: z.string().min(1, 'El email es requerido').email(vm.emailInvalid),
})

export const resetPasswordSchema = z
  .object({
    confirmationCode: z.string().min(1, 'El código es requerido'),
    newPassword: passwordField,
    confirmPassword: z.string().min(1, vm.passwordConfirmRequired),
  })
  .refine((v) => v.newPassword === v.confirmPassword, {
    message: vm.passwordsNoMatch,
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
