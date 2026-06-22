import { useCallback, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { authApi } from '../api'

interface ForgotPasswordState {
  loading: boolean
  error: ApiError | null
}

export function useForgotPassword() {
  const [state, setState] = useState<ForgotPasswordState>({ loading: false, error: null })

  const requestReset = useCallback(async (username: string): Promise<void> => {
    setState({ loading: true, error: null })
    try {
      await authApi.forgotPassword(username)
      setState({ loading: false, error: null })
    } catch (e) {
      const error = toApiError(e)
      setState({ loading: false, error })
      throw error
    }
  }, [])

  return { requestReset, ...state }
}
