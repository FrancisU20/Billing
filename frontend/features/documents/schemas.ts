import { z } from 'zod'
import { isDecimalInput, isPositiveDecimalInput } from '@/lib/utils/form-validators'
import { LINE_CODE_MAX_LENGTH } from './constants'

export const documentStatusSchema = z.enum([
  'PENDING',
  'PROCESSING',
  'AUTHORIZED',
  'REJECTED',
  'FAILED',
  'FAILED_PERMANENT',
  'ANNULLED',
])

export const ivaRateSchema = z.enum(['15', '5', '0', 'EXENTO'])

// Catálogo SRI: 04 RUC, 05 Cédula, 06 Pasaporte, 07 Consumidor Final, 08 Exterior
export const buyerIdTypeSchema = z.enum(['04', '05', '06', '07', '08'])

export const paymentMethodSchema = z.enum(['01', '15', '16', '17', '18', '19', '20', '21'])

export const sriErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  user_message: z.string().optional(),
  category: z.string().optional(),
  classification: z.enum(['PERMANENT', 'RETRYABLE']).optional(),
  raw_message: z.string().optional(),
  additional_info: z.string().nullable().optional(),
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
  annulled_at: z.string().nullable().optional().default(null),
  annulled_by: z.string().optional().default(''),
  annulment_reason: z.string().nullable().optional().default(null),
  related_document_id: z.string().nullable().optional().default(null),
  credit_note_reason: z.string().nullable().optional().default(null),
  manual_retry_count: z.coerce.number().optional().default(0),
  retried_at: z.string().nullable().optional().default(null),
  annulled_by_credit_note_id: z.string().nullable().optional().default(null),
})

export const documentsPageSchema = z.object({
  items: z.array(documentSchema),
  next_token: z.string().nullable(),
  has_more: z.boolean(),
  total: z.number().nullable().optional(),
})

export const dailyIssuedPointSchema = z.object({
  date: z.string().min(1),
  count: z.coerce.number(),
})

export const topClientSchema = z.object({
  client_id: z.string().min(1),
  name: z.string(),
  total: z.string().min(1),
})

export const documentsSummarySchema = z.object({
  period_start: z.string().min(1),
  period_end: z.string().min(1),
  issued_count: z.coerce.number(),
  authorized_count: z.coerce.number(),
  rejected_count: z.coerce.number(),
  failed_count: z.coerce.number(),
  pending_count: z.coerce.number(),
  processing_count: z.coerce.number(),
  authorized_total: z.string().min(1),
  credit_notes_count: z.coerce.number().optional().default(0),
  credit_notes_total: z.string().optional().default('0.00'),
  document_limit: z.coerce.number().nullable(),
  is_unlimited: z.boolean(),
  is_free_plan: z.boolean().optional().default(false),
  daily_issued: z.array(dailyIssuedPointSchema).optional().default([]),
  top_clients: z.array(topClientSchema).optional().default([]),
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
    code: z
      .string()
      .trim()
      .min(1, 'Requerido')
      .max(LINE_CODE_MAX_LENGTH, `Máximo ${LINE_CODE_MAX_LENGTH} caracteres`),
    description: z.string().trim().min(1, 'Requerido').max(300, 'Máximo 300 caracteres'),
    quantity: z.string().trim().refine(isDecimalInput, 'Cantidad inválida'),
    unit_price: z.string().trim().refine(isDecimalInput, 'Precio inválido'),
    discount: z.string().trim().refine(isDecimalInput, 'Descuento inválido'),
    iva_rate: ivaRateSchema,
  })
  .superRefine((line, ctx) => {
    const quantity = Number(line.quantity)
    const unitPrice = Number(line.unit_price)
    const discount = Number(line.discount)
    const gross = quantity * unitPrice

    if (!isPositiveDecimalInput(line.quantity) || !Number.isFinite(quantity)) {
      ctx.addIssue({
        code: 'custom',
        path: ['quantity'],
        message: 'Debe ser mayor a cero',
      })
    }
    if (!isPositiveDecimalInput(line.unit_price) || !Number.isFinite(unitPrice)) {
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
    override_discount_ceiling: z.boolean(),
    override_reason: z.string().trim().max(300, 'Máximo 300 caracteres').nullable(),
  })
  .superRefine((values, ctx) => {
    if (values.override_discount_ceiling && !values.override_reason?.trim()) {
      ctx.addIssue({
        code: 'custom',
        path: ['override_reason'],
        message: 'Indica el motivo para anular el techo de descuento',
      })
    }
  })
  .strict()

// Modo de selección del comprador — solo UI, no se envía al backend. Sin modo "manual":
// todo comprador que no sea Consumidor Final debe ser un Client real y guardado, nunca
// texto libre que no se persiste en ningún registro.
export const buyerModeSchema = z.enum(['consumidor_final', 'cliente'])

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
    override_discount_ceiling: z.boolean(),
    override_reason: z.string().trim().max(300, 'Máximo 300 caracteres'),
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
    if (values.override_discount_ceiling && !values.override_reason.trim()) {
      ctx.addIssue({
        code: 'custom',
        path: ['override_reason'],
        message: 'Indica el motivo para anular el techo de descuento',
      })
    }
  })
  .strict()

// ── Nota de Crédito ───────────────────────────────────────────────────────────
// Campos genuinamente distintos a factura (sin buyer-picking, sin override de
// descuento) — esquema propio en vez de forzar opcionales sobre emitDocumentSchema.

export const creditNoteLineInputSchema = z
  .object({
    parent_line_index: z.number().int().min(0),
    quantity: z.string().trim().refine(isPositiveDecimalInput, 'Cantidad inválida'),
  })
  .strict()

export const emitCreditNoteSchema = z
  .object({
    establishment_code: z
      .string()
      .trim()
      .regex(/^\d{3}$/, 'Debe tener 3 dígitos'),
    emission_point_code: z
      .string()
      .trim()
      .regex(/^\d{3}$/, 'Debe tener 3 dígitos'),
    doc_type: z.literal('04'),
    issued_at: z.string().trim().min(1, 'Requerido'),
    related_document_id: z.string().min(1),
    credit_note_reason: z.string().trim().min(1, 'Requerido').max(300, 'Máximo 300 caracteres'),
    lines: z.array(creditNoteLineInputSchema).min(1, 'Agrega al menos una línea'),
  })
  .strict()

// Una linea de la pantalla de NC: snapshot de la linea original (solo lectura) +
// la cantidad a acreditar, editable salvo cuando `locked` (entrada "Anular factura").
// original_subtotal/original_iva_amount permiten previsualizar el monto acreditado
// (escalado por cantidad/cantidad_original, igual que el backend) sin recalcular la
// tasa de IVA en el cliente — son solo para UI, el backend vuelve a calcular todo desde
// la factura padre y nunca confía en estos valores.
export const creditNoteFormLineSchema = z
  .object({
    parent_line_index: z.number().int().min(0),
    code: z.string(),
    description: z.string(),
    unit_price: z.string(),
    iva_rate: ivaRateSchema,
    original_quantity: z.string(),
    original_subtotal: z.string(),
    original_iva_amount: z.string(),
    quantity: z.string().trim().refine(isPositiveDecimalInput, 'Debe ser mayor a cero'),
  })
  .strict()

export const emitCreditNoteFormValuesSchema = z
  .object({
    establishment_code: z.string(),
    emission_point_code: z.string(),
    issued_at: z.string().trim().min(1, 'Requerido'),
    credit_note_reason: z.string().trim().min(1, 'Requerido').max(300, 'Máximo 300 caracteres'),
    lines: z.array(creditNoteFormLineSchema).min(1),
    locked: z.boolean(),
  })
  .superRefine((values, ctx) => {
    values.lines.forEach((line, index) => {
      const quantity = Number(line.quantity)
      const original = Number(line.original_quantity)
      if (quantity > original) {
        ctx.addIssue({
          code: 'custom',
          path: ['lines', index, 'quantity'],
          message: 'No puede superar la cantidad original',
        })
      }
    })
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
export type DocumentsSummary = z.infer<typeof documentsSummarySchema>
export type EmitDocumentResult = z.infer<typeof emitDocumentResultSchema>
export type EmitDocumentLineInput = z.infer<typeof emitDocumentLineSchema>
export type EmitDocumentInput = z.infer<typeof emitDocumentSchema>
export type BuyerMode = z.infer<typeof buyerModeSchema>
export type EmitDocumentFormValues = z.infer<typeof emitDocumentFormValuesSchema>
export type CreditNoteLineInput = z.infer<typeof creditNoteLineInputSchema>
export type EmitCreditNoteInput = z.infer<typeof emitCreditNoteSchema>
export type CreditNoteFormLine = z.infer<typeof creditNoteFormLineSchema>
export type EmitCreditNoteFormValues = z.infer<typeof emitCreditNoteFormValuesSchema>
