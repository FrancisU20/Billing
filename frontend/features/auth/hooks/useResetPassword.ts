import { useCallback, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { authApi } from '../api'
import type { ConfirmForgotPasswordCredentials } from '../types'

interface ResetPasswordState {
  loading: boolean
  error: ApiError | null
}

export function useResetPassword() {
  const [state, setState] = useState<ResetPasswordState>({ loading: false, error: null })

  const resetPassword = useCallback(
    async (creds: ConfirmForgotPasswordCredentials): Promise<void> => {
      setState({ loading: true, error: null })
      try {
        await authApi.resetPassword(creds)
        setState({ loading: false, error: null })
      } catch (e) {
        const error = toApiError(e)
        setState({ loading: false, error })
        throw error
      }
    },
    [],
  )

  return { resetPassword, ...state }
}
