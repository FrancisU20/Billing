import { describe, expect, it } from 'vitest'
import {
  documentSchema,
  documentsPageSchema,
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
  buyer_name: 'Consumidor Final',
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

  it('matches paginated GET /documents response', () => {
    expect(
      documentsPageSchema.parse({ items: [document], next_token: null, has_more: false }),
    ).toEqual({ items: [document], next_token: null, has_more: false })
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
      buyer_name: 'Consumidor Final',
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
    }

    expect(formValuesToEmitDocumentInput(values)).toEqual({
      establishment_code: '001',
      emission_point_code: '001',
      doc_type: '01',
      issued_at: '2026-06-18',
      client_id: null,
      buyer_id_type: '07',
      buyer_id: '9999999999999',
      buyer_name: 'Consumidor Final',
      buyer_email: null,
      payment_method: '01',
      lines: values.lines,
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
        buyer_name: 'Consumidor Final',
        payment_method: '01',
        lines: [],
      }),
    ).toThrow()
  })
})
