import { z } from 'zod'

export const clientStatusSchema = z.enum(['active', 'inactive'])
export const identificationTypeSchema = z.enum(['ruc', 'cedula', 'pasaporte', 'exterior'])
export const personTypeSchema = z.enum(['natural', 'juridica'])

export const clientAddressSchema = z.object({
  label: z.string().min(1),
  line: z.string().min(1),
  city: z.string(),
})

export const clientSchema = z.object({
  id: z.string().min(1),
  tenant_id: z.string().min(1),
  identification: z.string().min(1),
  identification_type: identificationTypeSchema,
  person_type: personTypeSchema,
  legal_name: z.string().min(1),
  trade_name: z.string(),
  special_taxpayer: z.boolean(),
  emails: z.array(z.string()),
  phones: z.array(z.string()),
  addresses: z.array(clientAddressSchema),
  status: clientStatusSchema,
  created_at: z.string().min(1),
  updated_at: z.string().min(1),
  created_by: z.string(),
  updated_by: z.string(),
  version: z.coerce.number(),
})

export const clientsPageSchema = z.object({
  items: z.array(clientSchema),
  next_token: z.string().nullable(),
  has_more: z.boolean(),
  total: z.number().nullable().optional(),
})

export const createClientSchema = z
  .object({
    identification: z.string().trim().min(3, 'Mínimo 3 caracteres').max(25, 'Máximo 25 caracteres'),
    identification_type: identificationTypeSchema,
    person_type: personTypeSchema,
    legal_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(250, 'Máximo 250 caracteres'),
    trade_name: z.string().trim().max(250, 'Máximo 250 caracteres'),
    special_taxpayer: z.boolean(),
    emails: z.array(z.string().trim().email('Email inválido')).max(5, 'Máximo 5 emails'),
    phones: z.array(z.string().trim().min(7, 'Mínimo 7 caracteres')).max(5, 'Máximo 5 teléfonos'),
    addresses: z.array(clientAddressSchema).max(5, 'Máximo 5 direcciones'),
  })
  .strict()

export const updateClientSchema = createClientSchema
  .extend({
    status: clientStatusSchema.optional(),
  })
  .partial()
  .strict()

export const clientFormValuesSchema = z.object({
  identification: z.string().trim().min(3, 'Mínimo 3 caracteres').max(25, 'Máximo 25 caracteres'),
  identification_type: identificationTypeSchema,
  person_type: personTypeSchema,
  legal_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(250, 'Máximo 250 caracteres'),
  trade_name: z.string().trim().max(250, 'Máximo 250 caracteres'),
  special_taxpayer: z.boolean(),
  email: z.string().trim().email('Email inválido').or(z.literal('')),
  phone: z.string().trim().min(7, 'Mínimo 7 caracteres').or(z.literal('')),
  address_label: z.string().trim().max(50, 'Máximo 50 caracteres'),
  address_line: z.string().trim().max(500, 'Máximo 500 caracteres'),
  address_city: z.string().trim().max(100, 'Máximo 100 caracteres'),
  status: clientStatusSchema,
})

export type Client = z.infer<typeof clientSchema>
export type ClientStatus = z.infer<typeof clientStatusSchema>
export type IdentificationType = z.infer<typeof identificationTypeSchema>
export type PersonType = z.infer<typeof personTypeSchema>
export type ClientAddress = z.infer<typeof clientAddressSchema>
export type ClientsPage = z.infer<typeof clientsPageSchema>
export type CreateClientInput = z.infer<typeof createClientSchema>
export type UpdateClientInput = z.infer<typeof updateClientSchema>
export type ClientFormValues = z.infer<typeof clientFormValuesSchema>
