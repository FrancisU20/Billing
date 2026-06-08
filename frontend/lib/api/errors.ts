export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly statusCode: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }

  get isUnauthorized() { return this.statusCode === 401 }
  get isForbidden()    { return this.statusCode === 403 }
  get isNotFound()     { return this.statusCode === 404 }
  get isConflict()     { return this.statusCode === 409 }
  get isValidation()   { return this.code === 'VALIDATION_ERROR' }
  get isNetwork()      { return this.statusCode === 0 }
}

export function toApiError(e: unknown): ApiError {
  if (e instanceof ApiError) return e
  if (e instanceof Error) return new ApiError('NETWORK_ERROR', e.message, 0)
  return new ApiError('UNKNOWN_ERROR', 'Error inesperado', 0)
}
