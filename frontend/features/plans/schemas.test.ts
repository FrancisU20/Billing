import { describe, expect, it } from 'vitest'
import { createPlanSchema, planSchema, plansListSchema, updatePlanSchema } from './schemas'

const plan = {
  id: 'plan-1',
  slug: 'basic',
  name: 'Basic',
  description: 'Plan inicial',
  monthly_price: '19.99',
  annual_price: '199.99',
  document_limit: 100,
  limit_cycle: 'month',
  max_locations: 1,
  max_emission_points: 1,
  max_users: 3,
  includes_credit_notes: true,
  includes_withholdings: true,
  includes_delivery_notes: true,
  includes_api: false,
  order: 1,
  active: true,
  version: '1',
  created_at: '2026-06-08T00:00:00Z',
  updated_at: '2026-06-08T00:00:00Z',
  created_by: 'user-1',
}

describe('plan contract schemas', () => {
  it('accepts the backend plan shape', () => {
    expect(planSchema.parse(plan)).toEqual({ ...plan, version: 1 })
  })

  it('matches the non-paginated GET /plans response', () => {
    expect(plansListSchema.parse({ items: [plan] })).toEqual({ items: [{ ...plan, version: 1 }] })
    expect(() =>
      plansListSchema.parse({ items: [plan], next_token: null, has_more: false }),
    ).not.toThrow()
  })

  it('validates create and update payload constraints', () => {
    expect(() =>
      createPlanSchema.parse({
        slug: 'enterprise_2026',
        name: 'Enterprise',
        document_limit: -1,
      }),
    ).not.toThrow()

    expect(() =>
      createPlanSchema.parse({ slug: 'Invalid Slug', name: 'A', document_limit: 1 }),
    ).toThrow()
    expect(() => updatePlanSchema.parse({ monthly_price: '29.99', order: 2 })).not.toThrow()
    expect(() => updatePlanSchema.parse({ slug: 'new-slug' })).toThrow()
  })
})
