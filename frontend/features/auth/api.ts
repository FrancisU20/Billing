import { api } from '@/lib/api/client'
import type { AuthChallenge, AuthTokens, ChallengeCredentials, LoginCredentials } from './types'

interface LoginResponse {
  id_token?: string
  access_token?: string
  refresh_token?: string
  challenge_name?: string
  session?: string
  parameters?: Record<string, string>
}

interface RefreshResponse {
  id_token: string
  access_token: string
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthTokens | AuthChallenge> => {
    const res = await api.post<LoginResponse>('/auth/login', credentials, { auth: false })

    if (res.challenge_name) {
      return {
        challenge_name: res.challenge_name,
        session: res.session!,
        parameters: res.parameters ?? {},
      }
    }

    return {
      idToken: res.id_token!,
      accessToken: res.access_token!,
      refreshToken: res.refresh_token!,
    }
  },

  refresh: async (refreshToken: string): Promise<Pick<AuthTokens, 'idToken' | 'accessToken'>> => {
    const res = await api.post<RefreshResponse>(
      '/auth/refresh',
      { refresh_token: refreshToken },
      { auth: false },
    )
    return { idToken: res.id_token, accessToken: res.access_token }
  },

  logout: async (accessToken: string): Promise<void> => {
    await api.post('/auth/logout', { access_token: accessToken }, { auth: false })
  },

  challenge: async (creds: ChallengeCredentials): Promise<AuthTokens | AuthChallenge> => {
    const res = await api.post<LoginResponse>('/auth/challenge', creds, { auth: false })

    if (res.challenge_name) {
      return {
        challenge_name: res.challenge_name,
        session: res.session!,
        parameters: res.parameters ?? {},
      }
    }

    return {
      idToken: res.id_token!,
      accessToken: res.access_token!,
      refreshToken: res.refresh_token!,
    }
  },
}
