import { useCallback, useState } from 'react'
import { useAuthStore } from '../store'
import { authApi } from '../api'

export function useLogout() {
  const [loading, setLoading] = useState(false)

  const logout = useCallback(async () => {
    const { accessToken, clearAuth } = useAuthStore.getState()
    setLoading(true)
    try {
      if (accessToken) await authApi.logout(accessToken)
    } finally {
      // clearAuth dispara la redirección a login — el componente se desmonta.
      // No hace falta guard de mounted porque el set de loading ocurre antes.
      await clearAuth()
    }
  }, [])

  return { logout, loading }
}
