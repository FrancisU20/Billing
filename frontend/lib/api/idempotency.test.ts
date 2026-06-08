import { describe, expect, it } from 'vitest'
import { createIdempotencyKey } from './idempotency'

describe('createIdempotencyKey', () => {
  it('generates scoped unique keys', () => {
    const first = createIdempotencyKey('tenant')
    const second = createIdempotencyKey('tenant')

    expect(first).toMatch(/^tenant_/)
    expect(second).toMatch(/^tenant_/)
    expect(first).not.toBe(second)
  })
})
