import { Redirect, Stack } from 'expo-router'
import { useAuthStore, selectIsSuperadmin, selectUser } from '@/features/auth/store'
import { AppShell } from '@/features/navigation/components/AppShell'
import { Routes } from '@/constants/routes'

export default function SuperadminLayout() {
  const isSuperadmin = useAuthStore(selectIsSuperadmin)
  const user = useAuthStore(selectUser)

  if (!isSuperadmin) {
    return <Redirect href={Routes.tenant.dashboard} />
  }

  return (
    <AppShell user={user}>
      <Stack screenOptions={{ headerShown: false }} />
    </AppShell>
  )
}
