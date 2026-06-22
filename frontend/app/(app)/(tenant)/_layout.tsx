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

  // New tenants (free or paid) confirm/change their plan before paying or uploading
  // a certificate. Gated on cert_uploaded_at too so tenants from the old flow (cert
  // already uploaded at registration) are never sent back here.
  const needsPlanConfirmation = !tenant?.plan_confirmed_at && !tenant?.cert_uploaded_at
  if (needsPlanConfirmation) {
    return <Redirect href={Routes.app.confirmPlan as Href} />
  }

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

  // Plan confirmed (free) or payment already done: certificate is the last onboarding
  // step. Reached only once isPendingPayment/needsPlanConfirmation are both false.
  if (!tenant?.cert_uploaded_at) {
    return <Redirect href={Routes.app.uploadCertificate as Href} />
  }

  return <Stack screenOptions={{ headerShown: false }} />
}
