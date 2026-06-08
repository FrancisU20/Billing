import { create } from 'zustand'
import type { AuthRole } from '@/constants/roles'
import { decodeJwtClaims } from '@/lib/utils/jwt'
import { tokenStorage } from './storage'
import type { AuthTokens, AuthUser } from './types'

interface AuthState {
  user: AuthUser | null
  idToken: string | null
  accessToken: string | null
  refreshToken: string | null
  hydrated: boolean
}

interface AuthActions {
  setTokens: (tokens: AuthTokens) => Promise<void>
  clearAuth: () => Promise<void>
  hydrate: () => Promise<void>
}

function buildUser(idToken: string): AuthUser {
  const claims = decodeJwtClaims(idToken)
  return {
    sub: claims.sub,
    email: claims.email ?? '',
    role: (claims['custom:role'] as AuthRole) ?? 'viewer',
    tenantId: claims['custom:tenant_id'] || null,
    isSuperadmin: claims['custom:is_superadmin'] === 'true',
  }
}

export const useAuthStore = create<AuthState & AuthActions>((set) => ({
  user: null,
  idToken: null,
  accessToken: null,
  refreshToken: null,
  hydrated: false,

  setTokens: async (tokens: AuthTokens) => {
    await tokenStorage.saveAll(tokens)
    set({
      idToken: tokens.idToken,
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      user: buildUser(tokens.idToken),
    })
  },

  clearAuth: async () => {
    await tokenStorage.clearAll()
    set({ user: null, idToken: null, accessToken: null, refreshToken: null })
  },

  hydrate: async () => {
    const tokens = await tokenStorage.loadAll()
    if (tokens) {
      set({
        idToken: tokens.idToken,
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken,
        user: buildUser(tokens.idToken),
      })
    }
    set({ hydrated: true })
  },
}))

export const selectIsAuthenticated = (s: AuthState) => s.hydrated && !!s.idToken
export const selectIsSuperadmin = (s: AuthState) => s.user?.isSuperadmin === true
export const selectRole = (s: AuthState) => s.user?.role ?? null
export const selectUser = (s: AuthState) => s.user
