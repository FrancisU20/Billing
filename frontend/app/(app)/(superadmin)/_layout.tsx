import { Redirect, Stack } from 'expo-router'
import { useAuthStore, selectIsSuperadmin } from '@/features/auth/store'
import { Routes } from '@/constants/routes'

export default function SuperadminLayout() {
  const isSuperadmin = useAuthStore(selectIsSuperadmin)

  if (!isSuperadmin) {
    return <Redirect href={Routes.tenant.dashboard} />
  }

  return <Stack screenOptions={{ headerShown: false }} />
}
