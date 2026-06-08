import { useCallback, useRef, useState } from 'react'
import { useAuthStore } from '../store'
import { authApi } from '../api'

export function useLogout() {
  const [loading, setLoading] = useState(false)
  const mounted = useRef(true)

  const logout = useCallback(async () => {
    const { accessToken, clearAuth } = useAuthStore.getState()
    setLoading(true)
    try {
      if (accessToken) await authApi.logout(accessToken)
    } finally {
      await clearAuth()
      if (mounted.current) setLoading(false)
    }
  }, [])

  return { logout, loading }
}
