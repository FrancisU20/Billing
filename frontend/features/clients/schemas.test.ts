import { describe, expect, it } from 'vitest'
import {
  clientFormValuesSchema,
  clientSchema,
  clientsPageSchema,
  createClientSchema,
} from './schemas'
import { formValuesToCreateClientInput } from './form'

const client = {
  id: 'client-1',
  tenant_id: 'tenant-1',
  identification: '1792146739001',
  identification_type: 'ruc',
  person_type: 'juridica',
  legal_name: 'Cliente Demo S.A.',
  trade_name: 'Cliente Demo',
  special_taxpayer: false,
  emails: ['facturacion@cliente.com'],
  phones: ['0999999999'],
  addresses: [{ label: 'Principal', line: 'Av. Principal', city: 'Quito' }],
  status: 'active',
  created_at: '2026-06-08T00:00:00+00:00',
  updated_at: '2026-06-08T00:00:00+00:00',
  created_by: 'user-1',
  updated_by: 'user-1',
  version: '1',
}

describe('client contract schemas', () => {
  it('accepts the backend client shape', () => {
    expect(clientSchema.parse(client)).toEqual({ ...client, version: 1 })
  })

  it('matches paginated GET /clients response', () => {
    expect(clientsPageSchema.parse({ items: [client], next_token: null, has_more: false })).toEqual(
      { items: [{ ...client, version: 1 }], next_token: null, has_more: false },
    )
  })

  it('builds the API payload from UI form values', () => {
    const values = clientFormValuesSchema.parse({
      identification: '1792146739001',
      identification_type: 'ruc',
      person_type: 'juridica',
      legal_name: 'Cliente Demo S.A.',
      trade_name: 'Cliente Demo',
      special_taxpayer: true,
      email: 'facturacion@cliente.com',
      phone: '0999999999',
      address_label: 'Principal',
      address_line: 'Av. Principal',
      address_city: 'Quito',
      status: 'active',
    })

    expect(formValuesToCreateClientInput(values)).toEqual({
      identification: '1792146739001',
      identification_type: 'ruc',
      person_type: 'juridica',
      legal_name: 'Cliente Demo S.A.',
      trade_name: 'Cliente Demo',
      special_taxpayer: true,
      emails: ['facturacion@cliente.com'],
      phones: ['0999999999'],
      addresses: [{ label: 'Principal', line: 'Av. Principal', city: 'Quito' }],
    })
  })

  it('rejects unsupported identification types', () => {
    expect(() =>
      createClientSchema.parse({
        identification: '1792146739001',
        identification_type: 'foreign',
        person_type: 'juridica',
        legal_name: 'Cliente Demo S.A.',
        trade_name: 'Cliente Demo',
        special_taxpayer: false,
        emails: [],
        phones: [],
        addresses: [],
      }),
    ).toThrow()
  })

  it('rejects invalid Ecuadorian RUC and cedula values in the form', () => {
    const base = {
      identification: '1792146739002',
      identification_type: 'ruc',
      person_type: 'juridica',
      legal_name: 'Cliente Demo S.A.',
      trade_name: 'Cliente Demo',
      special_taxpayer: false,
      email: 'facturacion@cliente.com',
      phone: '0999999999',
      address_label: 'Principal',
      address_line: 'Av. Principal',
      address_city: 'Quito',
      status: 'active',
    } as const

    expect(() => clientFormValuesSchema.parse(base)).toThrow(/RUC ecuatoriano inválido/)
    expect(() =>
      clientFormValuesSchema.parse({
        ...base,
        identification: '1710034066',
        identification_type: 'cedula',
      }),
    ).toThrow(/Cédula ecuatoriana inválida/)
  })

  it('rejects invalid email in the form before building the payload', () => {
    expect(() =>
      clientFormValuesSchema.parse({
        identification: '1792146739001',
        identification_type: 'ruc',
        person_type: 'juridica',
        legal_name: 'Cliente Demo S.A.',
        trade_name: 'Cliente Demo',
        special_taxpayer: false,
        email: 'correo-malo',
        phone: '0999999999',
        address_label: 'Principal',
        address_line: 'Av. Principal',
        address_city: 'Quito',
        status: 'active',
      }),
    ).toThrow(/Email inválido/)
  })
})
