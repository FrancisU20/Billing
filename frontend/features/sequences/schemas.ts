import { z } from 'zod'

export const emissionPointSchema = z.object({
  code: z.string().min(1),
  label: z.string().min(1),
  initial_sequential: z.coerce.number(),
})

export const establishmentSchema = z.object({
  code: z.string().min(1),
  label: z.string().min(1),
  tenant_id: z.string().min(1),
  emission_points: z.array(emissionPointSchema),
  version: z.coerce.number(),
  created_at: z.string().min(1),
  updated_at: z.string().min(1),
  created_by: z.string(),
  updated_by: z.string(),
})

export const establishmentsListSchema = z.object({
  items: z.array(establishmentSchema),
})

export const createEstablishmentSchema = z
  .object({
    code: z
      .string()
      .trim()
      .regex(/^\d{3}$/, 'Debe tener 3 dígitos (ej. 001)'),
    label: z.string().trim().min(1, 'Requerido').max(200, 'Máximo 200 caracteres'),
  })
  .strict()

export const addEmissionPointSchema = z
  .object({
    code: z
      .string()
      .trim()
      .regex(/^\d{3}$/, 'Debe tener 3 dígitos (ej. 001)'),
    label: z.string().trim().min(1, 'Requerido').max(200, 'Máximo 200 caracteres'),
    initial_sequential: z.coerce
      .number()
      .int('Debe ser un número entero')
      .min(1, 'Mínimo 1')
      .max(999_999_999, 'Máximo 999999999'),
  })
  .strict()

export const editEmissionPointSchema = z
  .object({
    label: z.string().trim().min(1, 'Requerido').max(200, 'Máximo 200 caracteres').optional(),
    initial_sequential: z.coerce
      .number()
      .int('Debe ser un número entero')
      .min(1, 'Mínimo 1')
      .max(999_999_999, 'Máximo 999999999')
      .optional(),
  })
  .strict()

export type EmissionPoint = z.infer<typeof emissionPointSchema>
export type Establishment = z.infer<typeof establishmentSchema>
export type EstablishmentsList = z.infer<typeof establishmentsListSchema>
export type CreateEstablishmentInput = z.infer<typeof createEstablishmentSchema>
export type AddEmissionPointInput = z.infer<typeof addEmissionPointSchema>
export type EditEmissionPointInput = z.infer<typeof editEmissionPointSchema>
