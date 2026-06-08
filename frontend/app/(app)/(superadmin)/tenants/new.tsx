import React, { useState } from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { TenantForm } from '@/features/tenants/components/TenantForm'
import { tenantsApi } from '@/features/tenants/api'
import { ACTIVE_PLANS_FILTER } from '@/features/plans/constants'
import { usePlans } from '@/features/plans/hooks/usePlans'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { useTheme } from '@/lib/theme-context'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useToast } from '@/components/feedback/Toast'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { formValuesToCreateTenantInput, type TenantFormValues } from '@/features/tenants/form'

export default function NewTenantScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { plans, loading: plansLoading, error: plansError, refresh } = usePlans(ACTIVE_PLANS_FILTER)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  async function handleSubmit(values: TenantFormValues) {
    setSubmitting(true)
    setError(null)
    try {
      const tenant = await tenantsApi.create(
        formValuesToCreateTenantInput(values),
        createIdempotencyKey('tenant_create'),
      )
      toast.success('Empresa creada')
      router.replace(Routes.superadmin.tenantDetail(tenant.id))
    } catch (e) {
      setError(toApiError(e))
    } finally {
      setSubmitting(false)
    }
  }

  if (plansLoading) return <LoadingSpinner fullScreen label="Cargando planes..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Nueva empresa" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {plansError ? (
          <ApiErrorBanner error={plansError} />
        ) : plans.length === 0 ? (
          <EmptyState
            icon="pricetags-outline"
            title="Sin planes disponibles"
            description="Configura al menos un plan activo antes de crear empresas."
            action={{ label: 'Reintentar', onPress: refresh }}
          />
        ) : (
          <TenantForm
            mode="create"
            plans={plans}
            onSubmit={handleSubmit}
            isLoading={submitting}
            apiError={error}
          />
        )}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], paddingBottom: spacing[12] },
})
