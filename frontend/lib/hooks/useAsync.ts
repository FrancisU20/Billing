import { useCallback, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'

interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: ApiError | null
}

export function useAsync<T, A extends unknown[]>(fn: (...args: A) => Promise<T>) {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: false,
    error: null,
  })

  const execute = useCallback(
    async (...args: A): Promise<T> => {
      setState({ data: null, loading: true, error: null })
      try {
        const data = await fn(...args)
        setState({ data, loading: false, error: null })
        return data
      } catch (e) {
        const error = toApiError(e)
        setState({ data: null, loading: false, error })
        throw error
      }
    },
    [fn],
  )

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null })
  }, [])

  return { ...state, execute, reset }
}
