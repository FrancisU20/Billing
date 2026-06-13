import { Redirect } from 'expo-router'
import { useAuthStore, selectIsAuthenticated, selectIsSuperadmin } from '@/features/auth/store'
import { LandingScreen } from '@/features/marketing/screens/LandingScreen'
import { Routes } from '@/constants/routes'

export default function Index() {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const isSuperadmin = useAuthStore(selectIsSuperadmin)

  if (!isAuthenticated) {
    return <LandingScreen />
  }

  if (isSuperadmin) {
    return <Redirect href={Routes.superadmin.tenants} />
  }

  return <Redirect href={Routes.tenant.dashboard} />
}
