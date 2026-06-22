import { api } from '@/lib/api/client'
import type {
  AuthChallenge,
  AuthTokens,
  ChallengeCredentials,
  ConfirmForgotPasswordCredentials,
  LoginCredentials,
} from './types'
import { forgotPasswordResponseSchema, loginResponseSchema, refreshResponseSchema } from './schemas'
import { z } from 'zod'

function mapLoginResponse(raw: unknown): AuthTokens | AuthChallenge {
  const res = loginResponseSchema.parse(raw)

  if ('challenge_name' in res) {
    return {
      challenge_name: res.challenge_name,
      session: res.session,
      parameters: res.parameters,
    }
  }

  return {
    idToken: res.id_token,
    accessToken: res.access_token,
    refreshToken: res.refresh_token,
  }
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthTokens | AuthChallenge> => {
    const res = await api.post('/auth/login', credentials, loginResponseSchema, { auth: false })
    return mapLoginResponse(res)
  },

  refresh: async (refreshToken: string): Promise<Pick<AuthTokens, 'idToken' | 'accessToken'>> => {
    const res = await api.post(
      '/auth/refresh',
      { refresh_token: refreshToken },
      refreshResponseSchema,
      { auth: false },
    )
    return { idToken: res.id_token, accessToken: res.access_token }
  },

  logout: async (accessToken: string): Promise<void> => {
    await api.post('/auth/logout', { access_token: accessToken }, z.void(), { auth: false })
  },

  challenge: async (creds: ChallengeCredentials): Promise<AuthTokens | AuthChallenge> => {
    const res = await api.post('/auth/challenge', creds, loginResponseSchema, { auth: false })
    return mapLoginResponse(res)
  },

  forgotPassword: async (username: string): Promise<string> => {
    const res = await api.post(
      '/auth/forgot-password',
      { username },
      forgotPasswordResponseSchema,
      { auth: false },
    )
    return res.message
  },

  resetPassword: async (creds: ConfirmForgotPasswordCredentials): Promise<void> => {
    await api.post(
      '/auth/reset-password',
      {
        username: creds.username,
        confirmation_code: creds.confirmationCode,
        new_password: creds.newPassword,
      },
      z.void(),
      { auth: false },
    )
  },
}
