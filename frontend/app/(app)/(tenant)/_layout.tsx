import { Redirect, Stack } from 'expo-router'
import type { Href } from 'expo-router'
import { useAuthStore, selectIsSuperadmin, selectUser } from '@/features/auth/store'
import { useTenant } from '@/features/tenants/hooks/useTenant'
import { Routes } from '@/constants/routes'

export default function TenantLayout() {
  const isSuperadmin = useAuthStore(selectIsSuperadmin)
  const user = useAuthStore(selectUser)
  const { tenant, loading } = useTenant(user?.tenantId ?? null)

  if (isSuperadmin) {
    return <Redirect href={Routes.superadmin.tenants} />
  }

  // Hold render until tenant loads to avoid a flash of dashboard before guard fires.
  if (loading || (user?.tenantId && !tenant)) return null

  if (tenant?.subscription_status === 'pending_payment') {
    return <Redirect href={Routes.app.activateSubscription as Href} />
  }

  return <Stack screenOptions={{ headerShown: false }} />
}
