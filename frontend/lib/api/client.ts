import { config } from '@/constants/config'
import { ApiError } from './errors'
import type { ApiEnvelope, RequestOptions } from './types'

let _getIdToken: (() => string | null) | null = null
let _getRefreshToken: (() => string | null) | null = null
let _onRefresh: (() => Promise<boolean>) | null = null
let _onSessionExpired: (() => void) | null = null

export function configureApiClient(opts: {
  getIdToken: () => string | null
  getRefreshToken: () => string | null
  onRefresh: () => Promise<boolean>
  onSessionExpired: () => void
}) {
  _getIdToken = opts.getIdToken
  _getRefreshToken = opts.getRefreshToken
  _onRefresh = opts.onRefresh
  _onSessionExpired = opts.onSessionExpired
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
  isRetry = false,
): Promise<T> {
  const { auth = true, idempotencyKey, headers: extraHeaders = {}, ...fetchOptions } = options

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extraHeaders,
  }

  if (auth && _getIdToken) {
    const token = _getIdToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  if (idempotencyKey) {
    headers['X-Idempotency-Key'] = idempotencyKey
  }

  let res: Response
  try {
    res = await fetch(`${config.apiUrl}${path}`, { ...fetchOptions, headers })
  } catch {
    throw new ApiError('NETWORK_ERROR', 'Sin conexión a internet', 0)
  }

  if (res.status === 401 && auth && !isRetry && _onRefresh) {
    const refreshed = await _onRefresh()
    if (refreshed) return request<T>(path, options, true)
    _onSessionExpired?.()
    throw new ApiError('UNAUTHORIZED', 'Sesión expirada', 401)
  }

  if (res.status === 204) return undefined as T

  const envelope: ApiEnvelope<T> = await res.json()

  if (!envelope.success) {
    throw new ApiError(
      envelope.error?.code ?? 'UNKNOWN_ERROR',
      envelope.error?.message ?? 'Error desconocido',
      res.status,
    )
  }

  return envelope.data as T
}

export const api = {
  get: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { method: 'GET', ...opts }),

  post: <T>(path: string, body: unknown, opts?: RequestOptions) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body), ...opts }),

  patch: <T>(path: string, body: unknown, opts?: RequestOptions) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body), ...opts }),

  delete: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { method: 'DELETE', ...opts }),
}
