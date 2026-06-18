import { describe, expect, it } from 'vitest'
import {
  addEmissionPointSchema,
  createEstablishmentSchema,
  establishmentSchema,
  establishmentsListSchema,
} from './schemas'

const establishment = {
  code: '001',
  label: 'Matriz',
  tenant_id: 'tenant-1',
  emission_points: [{ code: '099', label: 'Pruebas', initial_sequential: 1 }],
  version: 1,
  created_at: '2026-06-18T09:00:00+00:00',
  updated_at: '2026-06-18T09:00:00+00:00',
  created_by: 'user-1',
  updated_by: 'user-1',
}

describe('sequences contract schemas', () => {
  it('accepts the backend establishment shape', () => {
    expect(establishmentSchema.parse(establishment)).toEqual(establishment)
  })

  it('matches GET /tenants/{id}/establishments response', () => {
    expect(establishmentsListSchema.parse({ items: [establishment] })).toEqual({
      items: [establishment],
    })
  })

  it('rejects an establishment code that is not 3 digits', () => {
    expect(() => createEstablishmentSchema.parse({ code: '1', label: 'Sucursal' })).toThrow()
  })

  it('rejects an emission point initial_sequential out of range', () => {
    expect(() =>
      addEmissionPointSchema.parse({ code: '001', label: 'Caja 1', initial_sequential: 0 }),
    ).toThrow()
  })
})
