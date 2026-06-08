import { config } from '@/constants/config'
import { isTokenExpired } from '@/lib/utils/jwt'
import { ApiError } from './errors'
import type { ApiEnvelope, RequestOptions } from './types'
import type { ZodType } from 'zod'

let _getIdToken: (() => string | null) | null = null
let _onRefresh: (() => Promise<boolean>) | null = null
let _onSessionExpired: (() => void) | null = null

export function configureApiClient(opts: {
  getIdToken: () => string | null
  onRefresh: () => Promise<boolean>
  onSessionExpired: () => void
}) {
  _getIdToken = opts.getIdToken
  _onRefresh = opts.onRefresh
  _onSessionExpired = opts.onSessionExpired
}

async function request<T>(
  path: string,
  schema: ZodType<T>,
  options: RequestOptions = {},
  isRetry = false,
): Promise<T> {
  const { auth = true, idempotencyKey, headers: extraHeaders = {}, ...fetchOptions } = options

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extraHeaders,
  }

  if (auth && _getIdToken) {
    let token = _getIdToken()
    if (token && !isRetry && _onRefresh && isTokenExpired(token)) {
      const refreshed = await _onRefresh()
      if (!refreshed) {
        _onSessionExpired?.()
        throw new ApiError('UNAUTHORIZED', 'Sesión expirada', 401)
      }
      token = _getIdToken()
    }
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
    if (refreshed) return request(path, schema, options, true)
    _onSessionExpired?.()
    throw new ApiError('UNAUTHORIZED', 'Sesión expirada', 401)
  }

  if (res.status === 204) return schema.parse(undefined)

  let envelope: ApiEnvelope<unknown>
  try {
    envelope = await res.json()
  } catch {
    throw new ApiError('INVALID_API_RESPONSE', 'Respuesta inválida del servidor', res.status)
  }

  if (!envelope.success) {
    throw new ApiError(
      envelope.error?.code ?? 'UNKNOWN_ERROR',
      envelope.error?.message ?? 'Error desconocido',
      res.status,
    )
  }

  return schema.parse(envelope.data)
}

export const api = {
  get: <T>(path: string, schema: ZodType<T>, opts?: RequestOptions) =>
    request(path, schema, { method: 'GET', ...opts }),

  post: <T>(path: string, body: unknown, schema: ZodType<T>, opts?: RequestOptions) =>
    request(path, schema, { method: 'POST', body: JSON.stringify(body), ...opts }),

  patch: <T>(path: string, body: unknown, schema: ZodType<T>, opts?: RequestOptions) =>
    request(path, schema, { method: 'PATCH', body: JSON.stringify(body), ...opts }),

  delete: <T>(path: string, schema: ZodType<T>, opts?: RequestOptions) =>
    request(path, schema, { method: 'DELETE', ...opts }),
}
