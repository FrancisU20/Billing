import { useCallback, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { authApi } from '../api'
import { useAuthStore } from '../store'
import type { AuthChallenge, AuthTokens, ChallengeCredentials, LoginResult } from '../types'

interface ChallengeState {
  loading: boolean
  error: ApiError | null
}

export function useChallenge() {
  const setTokens = useAuthStore((s) => s.setTokens)
  const [state, setState] = useState<ChallengeState>({ loading: false, error: null })

  const respond = useCallback(
    async (creds: ChallengeCredentials): Promise<LoginResult> => {
      setState({ loading: true, error: null })
      try {
        const res = await authApi.challenge(creds)

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

  return { respond, ...state }
}
