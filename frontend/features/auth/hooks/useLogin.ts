import { useCallback, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { authApi } from '../api'
import { useAuthStore } from '../store'
import type { AuthChallenge, AuthTokens, LoginCredentials, LoginResult } from '../types'

interface LoginState {
  loading: boolean
  error: ApiError | null
}

export function useLogin() {
  const setTokens = useAuthStore((s) => s.setTokens)
  const [state, setState] = useState<LoginState>({ loading: false, error: null })

  const login = useCallback(
    async (credentials: LoginCredentials): Promise<LoginResult> => {
      setState({ loading: true, error: null })
      try {
        const res = await authApi.login(credentials)

        if ('challenge_name' in res) {
          setState({ loading: false, error: null })
          return { type: 'challenge', challenge: res as AuthChallenge }
        }

        await setTokens(res as AuthTokens)
        setState({ loading: false, error: null })
        return { type: 'success' }
      } catch (e) {
        const error = toApiError(e)
        setState({ loading: false, error })
        throw error
      }
    },
    [setTokens],
  )

  return { login, ...state }
}
