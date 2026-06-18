import { z } from 'zod'

export const documentStatusSchema = z.enum([
  'PENDING',
  'PROCESSING',
  'AUTHORIZED',
  'REJECTED',
  'FAILED',
  'FAILED_PERMANENT',
])

export const ivaRateSchema = z.enum(['15', '5', '0', 'EXENTO'])

// Catálogo SRI: 04 RUC, 05 Cédula, 06 Pasaporte, 07 Consumidor Final, 08 Exterior
export const buyerIdTypeSchema = z.enum(['04', '05', '06', '07', '08'])

export const paymentMethodSchema = z.enum(['01', '15', '16', '17', '18', '19', '20', '21'])

export const sriErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
})

export const documentLineSchema = z.object({
  product_id: z.string().nullable().optional(),
  code: z.string().min(1),
  description: z.string().min(1),
  quantity: z.string().min(1),
  unit_price: z.string().min(1),
  discount: z.string().min(1),
  subtotal: z.string().min(1),
  iva_rate: ivaRateSchema,
  iva_amount: z.string().min(1),
  total: z.string().min(1),
})

export const documentSchema = z.object({
  document_id: z.string().min(1),
  tenant_id: z.string().min(1),
  doc_type: z.string().min(1),
  status: documentStatusSchema,
  serie: z.string().min(1),
  sequential: z.coerce.number(),
  sequential_display: z.string().min(1),
  access_key: z.string().min(1),
  client_id: z.string().nullable(),
  buyer_id_type: buyerIdTypeSchema,
  buyer_id: z.string().min(1),
  buyer_name: z.string().min(1),
  buyer_email: z.string().nullable(),
  issued_at: z.string().min(1),
  sri_environment: z.string().min(1),
  subtotal: z.string().min(1),
  total_discount: z.string().min(1),
  iva_15: z.string().min(1),
  iva_5: z.string().min(1),
  iva_0: z.string().min(1),
  total: z.string().min(1),
  payment_method: paymentMethodSchema,
  lines: z.array(documentLineSchema),
  retry_count: z.coerce.number(),
  authorization_number: z.string().nullable(),
  authorized_at: z.string().nullable(),
  rejected_at: z.string().nullable(),
  xml_s3_key: z.string().nullable(),
  ride_s3_key: z.string().nullable(),
  sri_errors: z.array(sriErrorSchema).nullable(),
  created_at: z.string().min(1),
  updated_at: z.string().min(1),
  created_by: z.string(),
})

export const documentsPageSchema = z.object({
  items: z.array(documentSchema),
  next_token: z.string().nullable(),
  has_more: z.boolean(),
})

export const rideUrlSchema = z.object({
  url: z.string().min(1),
})

// POST /documents responde 202 con un subconjunto del documento — no el
// documento completo (ver lambdas/documents/handler.py::_emit). El resto de
// los campos se obtienen recién al hacer GET /documents/{id}.
export const emitDocumentResultSchema = z.object({
  document_id: z.string().min(1),
  access_key: z.string().min(1),
  sequential: z.coerce.number(),
  sequential_display: z.string().min(1),
  status: documentStatusSchema,
})

export const emitDocumentLineSchema = z
  .object({
    product_id: z.string().nullable().optional(),
    code: z.string().trim().min(1, 'Requerido').max(25, 'Máximo 25 caracteres'),
    description: z.string().trim().min(1, 'Requerido').max(300, 'Máximo 300 caracteres'),
    quantity: z
      .string()
      .trim()
      .regex(/^\d+(\.\d{1,2})?$/, 'Cantidad inválida'),
    unit_price: z
      .string()
      .trim()
      .regex(/^\d+(\.\d{1,2})?$/, 'Precio inválido'),
    discount: z
      .string()
      .trim()
      .regex(/^\d+(\.\d{1,2})?$/, 'Descuento inválido'),
    iva_rate: ivaRateSchema,
  })
  .superRefine((line, ctx) => {
    const quantity = Number(line.quantity)
    const unitPrice = Number(line.unit_price)
    const discount = Number(line.discount)
    const gross = quantity * unitPrice

    if (!Number.isFinite(quantity) || quantity <= 0) {
      ctx.addIssue({
        code: 'custom',
        path: ['quantity'],
        message: 'Debe ser mayor a cero',
      })
    }
    if (!Number.isFinite(unitPrice) || unitPrice <= 0) {
      ctx.addIssue({
        code: 'custom',
        path: ['unit_price'],
        message: 'Debe ser mayor a cero',
      })
    }
    if (Number.isFinite(discount) && discount > gross) {
      ctx.addIssue({
        code: 'custom',
        path: ['discount'],
        message: 'No puede superar el subtotal',
      })
    }
  })
  .strict()

export const emitDocumentSchema = z
  .object({
    establishment_code: z
      .string()
      .trim()
      .regex(/^\d{3}$/, 'Debe tener 3 dígitos'),
    emission_point_code: z
      .string()
      .trim()
      .regex(/^\d{3}$/, 'Debe tener 3 dígitos'),
    doc_type: z.literal('01'),
    issued_at: z.string().trim().min(1, 'Requerido'),
    client_id: z.string().nullable().optional(),
    buyer_id_type: buyerIdTypeSchema,
    buyer_id: z.string().trim().min(5, 'Mínimo 5 caracteres').max(20, 'Máximo 20 caracteres'),
    buyer_name: z.string().trim().min(1, 'Requerido').max(300, 'Máximo 300 caracteres'),
    buyer_email: z.string().trim().email('Email inválido').or(z.literal('')).nullable().optional(),
    payment_method: paymentMethodSchema,
    lines: z.array(emitDocumentLineSchema).min(1, 'Agrega al menos una línea'),
  })
  .strict()

// Modo de selección del comprador — solo UI, no se envía al backend.
export const buyerModeSchema = z.enum(['consumidor_final', 'cliente', 'manual'])

export const emitDocumentFormValuesSchema = z
  .object({
    establishment_code: z.string(),
    emission_point_code: z.string(),
    issued_at: z.string().trim().min(1, 'Requerido'),
    buyer_mode: buyerModeSchema,
    client_id: z.string().nullable(),
    buyer_id_type: buyerIdTypeSchema,
    buyer_id: z.string().trim().min(1, 'Requerido'),
    buyer_name: z.string().trim().min(1, 'Requerido'),
    buyer_email: z.string().trim().email('Email inválido').or(z.literal('')),
    payment_method: paymentMethodSchema,
    lines: z.array(emitDocumentLineSchema).min(1, 'Agrega al menos una línea'),
  })
  .superRefine((values, ctx) => {
    if (values.buyer_mode === 'consumidor_final') {
      if (values.buyer_id_type !== '07' || values.buyer_id !== '9999999999999') {
        ctx.addIssue({
          code: 'custom',
          path: ['buyer_id'],
          message: 'Consumidor Final debe usar 9999999999999',
        })
      }
    }
    if (values.buyer_mode === 'cliente' && !values.client_id) {
      ctx.addIssue({
        code: 'custom',
        path: ['client_id'],
        message: 'Selecciona un cliente',
      })
    }
  })
  .strict()

export type DocumentStatus = z.infer<typeof documentStatusSchema>
export type IvaRate = z.infer<typeof ivaRateSchema>
export type BuyerIdType = z.infer<typeof buyerIdTypeSchema>
export type PaymentMethod = z.infer<typeof paymentMethodSchema>
export type SriErrorDetail = z.infer<typeof sriErrorSchema>
export type DocumentLine = z.infer<typeof documentLineSchema>
export type Document = z.infer<typeof documentSchema>
export type DocumentsPage = z.infer<typeof documentsPageSchema>
export type EmitDocumentResult = z.infer<typeof emitDocumentResultSchema>
export type EmitDocumentLineInput = z.infer<typeof emitDocumentLineSchema>
export type EmitDocumentInput = z.infer<typeof emitDocumentSchema>
export type BuyerMode = z.infer<typeof buyerModeSchema>
export type EmitDocumentFormValues = z.infer<typeof emitDocumentFormValuesSchema>
