export function createIdempotencyKey(prefix = 'ui'): string {
  const randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)
  if (randomUUID) return `${prefix}_${randomUUID()}`

  const timestamp = Date.now().toString(36)
  const random = Math.random().toString(36).slice(2, 12)
  return `${prefix}_${timestamp}_${random}`
}
