import { describe, expect, it } from 'vitest'
import {
  documentSchema,
  documentsPageSchema,
  documentsSummarySchema,
  emitDocumentResultSchema,
  emitDocumentSchema,
} from './schemas'
import { formValuesToEmitDocumentInput } from './form'
import type { EmitDocumentFormValues } from './schemas'

const document = {
  document_id: 'doc-1',
  tenant_id: 'tenant-1',
  doc_type: '01',
  status: 'AUTHORIZED',
  serie: '001001',
  sequential: 1,
  sequential_display: '001-001-000000001',
  access_key: '1'.repeat(49),
  client_id: null,
  buyer_id_type: '07',
  buyer_id: '9999999999999',
  buyer_name: 'CONSUMIDOR FINAL',
  buyer_email: null,
  issued_at: '2026-06-18',
  sri_environment: 'testing',
  subtotal: '100.00',
  total_discount: '0.00',
  iva_15: '15.00',
  iva_5: '0.00',
  iva_0: '0.00',
  total: '115.00',
  payment_method: '01',
  lines: [
    {
      code: 'P1',
      description: 'Producto 1',
      quantity: '1',
      unit_price: '100.00',
      discount: '0.00',
      subtotal: '100.00',
      iva_rate: '15',
      iva_amount: '15.00',
      total: '115.00',
    },
  ],
  retry_count: 0,
  authorization_number: '1'.repeat(49),
  authorized_at: '2026-06-18T10:00:00+00:00',
  rejected_at: null,
  xml_s3_key: 'tenants/tenant-1/docs/2026/doc-1.xml',
  ride_s3_key: 'tenants/tenant-1/docs/2026/doc-1.pdf',
  sri_errors: null,
  created_at: '2026-06-18T09:00:00+00:00',
  updated_at: '2026-06-18T10:00:00+00:00',
  created_by: 'user-1',
}

describe('document contract schemas', () => {
  it('accepts the backend document shape', () => {
    expect(documentSchema.parse(document)).toEqual(document)
  })

  it('accepts normalized SRI errors', () => {
    const parsed = documentSchema.parse({
      ...document,
      status: 'REJECTED',
      sri_errors: [
        {
          code: '69',
          message: 'Identificación del receptor',
          user_message:
            'El SRI no reconoce la identificación del comprador. Para Consumidor Final debe usarse tipo 07 e identificación 9999999999999.',
          category: 'RECEPTOR',
          classification: 'PERMANENT',
          raw_message: 'ERROR EN LA IDENTIFICACION DEL RECEPTOR',
          additional_info: null,
        },
      ],
    })

    expect(parsed.sri_errors?.[0].user_message).toContain('tipo 07')
  })

  it('matches paginated GET /documents response', () => {
    expect(
      documentsPageSchema.parse({ items: [document], next_token: null, has_more: false }),
    ).toEqual({ items: [document], next_token: null, has_more: false })
  })

  it('matches GET /documents/summary response', () => {
    expect(
      documentsSummarySchema.parse({
        period_start: '2026-06-01',
        period_end: '2026-06-19',
        issued_count: 8,
        authorized_count: 5,
        rejected_count: 1,
        failed_count: 1,
        pending_count: 1,
        processing_count: 0,
        authorized_total: '199.95',
        document_limit: 500,
        is_unlimited: false,
        is_free_plan: false,
      }),
    ).toEqual({
      period_start: '2026-06-01',
      period_end: '2026-06-19',
      issued_count: 8,
      authorized_count: 5,
      rejected_count: 1,
      failed_count: 1,
      pending_count: 1,
      processing_count: 0,
      authorized_total: '199.95',
      document_limit: 500,
      is_unlimited: false,
      is_free_plan: false,
    })
  })

  it('matches GET /documents/summary response when the plan limit could not be resolved', () => {
    expect(
      documentsSummarySchema.parse({
        period_start: '2026-06-01',
        period_end: '2026-06-19',
        issued_count: 8,
        authorized_count: 5,
        rejected_count: 1,
        failed_count: 1,
        pending_count: 1,
        processing_count: 0,
        authorized_total: '199.95',
        document_limit: null,
        is_unlimited: false,
      }).document_limit,
    ).toBeNull()
  })

  it('builds the API payload from UI form values', () => {
    const values: EmitDocumentFormValues = {
      establishment_code: '001',
      emission_point_code: '001',
      issued_at: '2026-06-18',
      buyer_mode: 'consumidor_final',
      client_id: null,
      buyer_id_type: '07',
      buyer_id: '9999999999999',
      buyer_name: 'CONSUMIDOR FINAL',
      buyer_email: '',
      payment_method: '01',
      lines: [
        {
          code: 'P1',
          description: 'Producto 1',
          quantity: '1',
          unit_price: '100.00',
          discount: '0.00',
          iva_rate: '15',
        },
      ],
      override_discount_ceiling: false,
      override_reason: '',
    }

    expect(formValuesToEmitDocumentInput(values)).toEqual({
      establishment_code: '001',
      emission_point_code: '001',
      doc_type: '01',
      issued_at: '2026-06-18',
      client_id: null,
      buyer_id_type: '07',
      buyer_id: '9999999999999',
      buyer_name: 'CONSUMIDOR FINAL',
      buyer_email: null,
      payment_method: '01',
      lines: values.lines,
      override_discount_ceiling: false,
      override_reason: null,
    })
  })

  it('normalizes consumidor final when previous buyer state is stale', () => {
    const values: EmitDocumentFormValues = {
      establishment_code: '001',
      emission_point_code: '001',
      issued_at: '2026-06-18',
      buyer_mode: 'consumidor_final',
      client_id: 'client-prev',
      buyer_id_type: '05',
      buyer_id: '1710034065',
      buyer_name: 'Cliente previo',
      buyer_email: 'prev@example.com',
      payment_method: '01',
      lines: [
        {
          code: 'P1',
          description: 'Producto 1',
          quantity: '1',
          unit_price: '100.00',
          discount: '0.00',
          iva_rate: '15',
        },
      ],
      override_discount_ceiling: false,
      override_reason: '',
    }

    expect(formValuesToEmitDocumentInput(values)).toMatchObject({
      client_id: null,
      buyer_id_type: '07',
      buyer_id: '9999999999999',
      buyer_name: 'CONSUMIDOR FINAL',
      buyer_email: null,
    })
  })

  it('matches the partial POST /documents (202) response — not the full document', () => {
    // lambdas/documents/handler.py::_emit solo devuelve este subconjunto;
    // el resto se obtiene recién con GET /documents/{id}.
    expect(
      emitDocumentResultSchema.parse({
        document_id: 'doc-1',
        access_key: '1'.repeat(49),
        sequential: 1,
        sequential_display: '001-001-000000001',
        status: 'PENDING',
      }),
    ).toEqual({
      document_id: 'doc-1',
      access_key: '1'.repeat(49),
      sequential: 1,
      sequential_display: '001-001-000000001',
      status: 'PENDING',
    })
  })

  it('rejects a document with no lines', () => {
    expect(() =>
      emitDocumentSchema.parse({
        establishment_code: '001',
        emission_point_code: '001',
        doc_type: '01',
        issued_at: '2026-06-18',
        buyer_id_type: '07',
        buyer_id: '9999999999999',
        buyer_name: 'CONSUMIDOR FINAL',
        payment_method: '01',
        lines: [],
      }),
    ).toThrow()
  })

  it('rejects a line with zero unit price', () => {
    expect(() =>
      emitDocumentSchema.parse({
        establishment_code: '001',
        emission_point_code: '001',
        doc_type: '01',
        issued_at: '2026-06-18',
        buyer_id_type: '07',
        buyer_id: '9999999999999',
        buyer_name: 'CONSUMIDOR FINAL',
        payment_method: '01',
        lines: [
          {
            code: 'P1',
            description: 'Producto 1',
            quantity: '1',
            unit_price: '0.00',
            discount: '0.00',
            iva_rate: '15',
          },
        ],
      }),
    ).toThrow()
  })

  it('rejects a discount above the line gross amount', () => {
    expect(() =>
      emitDocumentSchema.parse({
        establishment_code: '001',
        emission_point_code: '001',
        doc_type: '01',
        issued_at: '2026-06-18',
        buyer_id_type: '07',
        buyer_id: '9999999999999',
        buyer_name: 'CONSUMIDOR FINAL',
        payment_method: '01',
        lines: [
          {
            code: 'P1',
            description: 'Producto 1',
            quantity: '1',
            unit_price: '10.00',
            discount: '10.01',
            iva_rate: '15',
          },
        ],
      }),
    ).toThrow()
  })
})
