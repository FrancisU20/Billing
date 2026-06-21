import { Redirect, Stack } from 'expo-router'
import type { Href } from 'expo-router'
import { View } from 'react-native'
import { useAuthStore, selectIsSuperadmin, selectUser } from '@/features/auth/store'
import { useTenant } from '@/features/tenants/hooks/useTenant'
import { PendingActivationBanner } from '@/features/subscriptions/components/PendingActivationBanner'
import { PaymentFailedBanner } from '@/features/subscriptions/components/PaymentFailedBanner'
import { Routes } from '@/constants/routes'

export default function TenantLayout() {
  const isSuperadmin = useAuthStore(selectIsSuperadmin)
  const user = useAuthStore(selectUser)
  const { tenant, loading, refresh } = useTenant(user?.tenantId ?? null)

  if (isSuperadmin) {
    return <Redirect href={Routes.superadmin.dashboard} />
  }

  // Hold render until tenant loads to avoid a flash of dashboard before guard fires.
  if (loading || (user?.tenantId && !tenant)) return null

  const isPendingPayment = tenant?.subscription_status === 'pending_payment'
  const isPaymentFailed = tenant?.subscription_status === 'payment_failed'
  const hasPendingOrder = isPendingPayment && Boolean(tenant?.pending_order_id)

  // Payment confirmed but activation transaction failed: auto-activate via banner.
  if (hasPendingOrder) {
    return (
      <View style={{ flex: 1 }}>
        <PendingActivationBanner
          tenantId={tenant!.id}
          orderId={tenant!.pending_order_id!}
          onActivated={refresh}
        />
        <Stack screenOptions={{ headerShown: false }} />
      </View>
    )
  }

  // No confirmed payment yet: must complete payment first.
  if (isPendingPayment) {
    return <Redirect href={Routes.app.activateSubscription as Href} />
  }

  // Recurring charge failed: stay in dashboard but show actionable banner.
  if (isPaymentFailed) {
    return (
      <View style={{ flex: 1 }}>
        <PaymentFailedBanner tenantId={tenant!.id} onRetried={refresh} />
        <Stack screenOptions={{ headerShown: false }} />
      </View>
    )
  }

  return <Stack screenOptions={{ headerShown: false }} />
}
