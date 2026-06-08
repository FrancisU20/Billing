import { Redirect } from 'expo-router'
import { useAuthStore, selectIsAuthenticated, selectIsSuperadmin } from '@/features/auth/store'
import { Routes } from '@/constants/routes'

export default function Index() {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const isSuperadmin = useAuthStore(selectIsSuperadmin)

  if (!isAuthenticated) {
    return <Redirect href={Routes.auth.login} />
  }

  if (isSuperadmin) {
    return <Redirect href={Routes.superadmin.tenants} />
  }

  return <Redirect href={Routes.tenant.dashboard} />
}
