import { Redirect, Stack } from 'expo-router'
import { useAuthStore, selectIsAuthenticated } from '@/features/auth/store'
import { Routes } from '@/constants/routes'

export default function AppLayout() {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)

  if (!isAuthenticated) {
    return <Redirect href={Routes.auth.login} />
  }

  return <Stack screenOptions={{ headerShown: false }} />
}
