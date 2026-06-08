export interface JwtClaims {
  sub: string
  email?: string
  'custom:role'?: string
  'custom:tenant_id'?: string
  'custom:is_superadmin'?: string
  exp?: number
}

export function decodeJwtClaims(token: string): JwtClaims {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return { sub: '' }
    const payload = parts[1]
    const padded = payload + '='.repeat((4 - (payload.length % 4)) % 4)
    const decoded = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded) as JwtClaims
  } catch {
    return { sub: '' }
  }
}

export function isTokenExpired(token: string): boolean {
  const claims = decodeJwtClaims(token)
  if (!claims.exp) return true
  return Date.now() / 1000 > claims.exp - 60
}
