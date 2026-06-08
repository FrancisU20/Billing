export interface ApiEnvelope<T> {
  success: boolean
  data: T | null
  error: { code: string; message: string } | null
  meta: { request_id: string; timestamp: string }
}

export interface PaginatedData<T> {
  items: T[]
  next_token: string | null
  has_more: boolean
}

export interface RequestOptions extends Omit<RequestInit, 'headers'> {
  auth?: boolean
  idempotencyKey?: string
  headers?: Record<string, string>
}
