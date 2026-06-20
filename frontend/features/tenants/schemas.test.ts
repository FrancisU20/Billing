import { describe, expect, it } from 'vitest'
import {
  createTenantSchema,
  tenantSchema,
  tenantsPageSchema,
  toggleTenantStatusSchema,
  updateTenantSchema,
} from './schemas'

const tenant = {
  id: 'tenant-1',
  ruc: '1792146739001',
  trade_name: 'CodeLabs',
  legal_name: 'CodeLabs S.A.',
  legal_rep_name: 'Pancho Ulloa',
  email: 'admin@codelabs.ec',
  phone: '0999999999',
  address: 'Quito',
  accounting_required: false,
  sri_environment: 'testing',
  status: 'active',
  plan_id: 'plan-1',
  plan_status: 'active',
  plan_cycle_ends_at: null,
  cert_subject_ruc: null,
  cert_expires_at: null,
  cert_issuer: null,
  cert_uploaded_at: null,
  cert_expiry_alert_60_sent_at: null,
  cert_expiry_alert_30_sent_at: null,
  onboarding_completed_at: null,
  created_at: '2026-06-08T00:00:00Z',
  updated_at: '2026-06-08T00:00:00Z',
  created_by: 'user-1',
  version: '3',
}

describe('tenant contract schemas', () => {
  it('accepts the backend tenant shape', () => {
    expect(tenantSchema.parse(tenant)).toEqual({ ...tenant, version: 3 })
  })

  it('rejects stale frontend fields that are not in the backend contract', () => {
    expect(() => tenantSchema.parse({ ...tenant, business_name: 'Legacy' })).not.toThrow()
    expect(() => tenantSchema.parse({ ...tenant, status: 'pending' })).toThrow()
  })

  it('validates paginated list metadata', () => {
    expect(tenantsPageSchema.parse({ items: [tenant], next_token: null, has_more: false })).toEqual(
      {
        items: [{ ...tenant, version: 3 }],
        next_token: null,
        has_more: false,
      },
    )
  })

  it('keeps create and update payloads scoped to writable fields', () => {
    const createPayload = {
      ruc: '1792146739001',
      trade_name: 'CodeLabs',
      legal_name: 'CodeLabs S.A.',
      legal_rep_name: 'Pancho Ulloa',
      email: 'admin@codelabs.ec',
      phone: '0999999999',
      address: 'Quito',
      accounting_required: false,
      plan_id: 'plan-1',
    }

    expect(() => createTenantSchema.parse(createPayload)).not.toThrow()
    expect(() => createTenantSchema.parse({ ...createPayload, id: 'tenant-1' })).toThrow()
    expect(() => updateTenantSchema.parse({ sri_environment: 'production' })).not.toThrow()
    expect(() => updateTenantSchema.parse({ created_at: '2026-06-08T00:00:00Z' })).toThrow()
    expect(() => toggleTenantStatusSchema.parse({ status: 'inactive' })).not.toThrow()
  })

  it('rejects invalid RUC and email in writable payloads', () => {
    const createPayload = {
      ruc: '1792146739002',
      trade_name: 'CodeLabs',
      legal_name: 'CodeLabs S.A.',
      legal_rep_name: 'Pancho Ulloa',
      email: 'admin@codelabs.ec',
      phone: '0999999999',
      address: 'Quito',
      accounting_required: false,
      plan_id: 'plan-1',
    }

    expect(() => createTenantSchema.parse(createPayload)).toThrow(/RUC ecuatoriano inválido/)
    expect(() => updateTenantSchema.parse({ email: 'correo-malo' })).toThrow(/Email inválido/)
  })
})
