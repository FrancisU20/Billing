import { Redirect, Stack } from 'expo-router'
import { useAuthStore, selectIsAuthenticated } from '@/features/auth/store'
import { Routes } from '@/constants/routes'

// No sidebar here: this layout also covers the mandatory onboarding screens
// (activate-subscription, confirm-plan, upload-certificate), which the user must
// not be able to navigate away from. The sidebar is rendered by (tenant)/_layout
// and (superadmin)/_layout instead, once their own gates have passed.
export default function AppLayout() {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)

  if (!isAuthenticated) {
    return <Redirect href={Routes.auth.login} />
  }

  return <Stack screenOptions={{ headerShown: false }} />
}
