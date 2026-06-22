import type { AuthRole } from '@/constants/roles'

export interface AuthTokens {
  idToken: string
  accessToken: string
  refreshToken: string
}

export interface AuthUser {
  sub: string
  email: string
  role: AuthRole
  tenantId: string | null
  isSuperadmin: boolean
}

export interface AuthChallenge {
  challenge_name: string
  session: string
  parameters: Record<string, string>
}

export type LoginResult = { type: 'success' } | { type: 'challenge'; challenge: AuthChallenge }

export interface LoginCredentials {
  username: string
  password: string
}

export interface ChallengeCredentials {
  session: string
  challenge_name: string
  responses: Record<string, string>
}

export interface ConfirmForgotPasswordCredentials {
  username: string
  confirmationCode: string
  newPassword: string
}
