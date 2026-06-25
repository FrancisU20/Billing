import { describe, expect, it } from 'vitest'
import { documentSchema } from './schemas'
import { getCreditNoteBlockReason } from './utils'

function makeDocument(overrides: Record<string, unknown> = {}) {
  return documentSchema.parse({
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
    issued_at: '2026-01-01',
    sri_environment: 'testing',
    subtotal: '100.00',
    total_discount: '0.00',
    iva_15: '15.00',
    iva_5: '0.00',
    iva_0: '0.00',
    total: '115.00',
    payment_method: '01',
    lines: [],
    retry_count: 0,
    authorization_number: null,
    authorized_at: null,
    rejected_at: null,
    xml_s3_key: null,
    ride_s3_key: null,
    sri_errors: null,
    created_at: '2026-01-01T09:00:00+00:00',
    updated_at: '2026-01-01T09:00:00+00:00',
    created_by: 'user-1',
    ...overrides,
  })
}

describe('getCreditNoteBlockReason', () => {
  it('allows an authorized invoice', () => {
    expect(getCreditNoteBlockReason(makeDocument())).toBeNull()
  })

  it('blocks a non-authorized document', () => {
    expect(getCreditNoteBlockReason(makeDocument({ status: 'PENDING' }))).not.toBeNull()
  })

  it('blocks a credit note referencing another credit note', () => {
    expect(getCreditNoteBlockReason(makeDocument({ doc_type: '04' }))).not.toBeNull()
  })

  // Regresion: a diferencia de la vieja anulacion local (deprecada), Nota de Credito NO
  // tiene excepcion de Consumidor Final ni ventana de plazo legal — eso es justo el fix
  // que motivo reemplazar el flujo viejo.
  it('does not block Consumidor Final invoices', () => {
    expect(
      getCreditNoteBlockReason(makeDocument({ buyer_id_type: '07', buyer_id: '9999999999999' })),
    ).toBeNull()
  })

  it('does not block invoices issued long ago (no plazo window)', () => {
    expect(getCreditNoteBlockReason(makeDocument({ issued_at: '2020-01-01' }))).toBeNull()
  })
})
