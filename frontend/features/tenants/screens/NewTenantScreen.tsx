import React from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { useTheme } from '@/lib/theme-context'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useToast } from '@/components/feedback/Toast'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { usePlans } from '@/features/plans/hooks/usePlans'
import { tenantsApi } from '../api'
import { TenantForm } from '../components/TenantForm'
import { formValuesToCreateTenantInput, type TenantFormValues } from '../form'

export function NewTenantScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { plans, loading: plansLoading, error: plansError, refresh } = usePlans()

  const { submitting, error, submit } = useFormSubmit(async (values: TenantFormValues) => {
    const tenant = await tenantsApi.create(
      formValuesToCreateTenantInput(values),
      createIdempotencyKey('tenant_create'),
    )
    toast.success('Empresa creada')
    router.replace(Routes.superadmin.tenantDetail(tenant.id))
  })

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
            onSubmit={submit}
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
