import React, { useState } from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { tenantsApi } from '../api'
import { TenantForm } from '../components/TenantForm'
import { formValuesToUpdateTenantInput, type TenantFormValues } from '../form'
import { useTenant } from '../hooks/useTenant'

export function EditTenantScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { tenant, loading, error } = useTenant(id ?? null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<ApiError | null>(null)

  async function handleSubmit(values: TenantFormValues) {
    if (!id) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const updated = await tenantsApi.update(
        id,
        formValuesToUpdateTenantInput(values),
        createIdempotencyKey('tenant_update'),
      )
      toast.success('Empresa actualizada')
      router.replace(Routes.superadmin.tenantDetail(updated.id) as Href)
    } catch (e) {
      setSubmitError(toApiError(e))
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <LoadingSpinner fullScreen label="Cargando empresa..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Editar empresa" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {error ? <ApiErrorBanner error={error} /> : null}
        {tenant ? (
          <TenantForm
            mode="edit"
            tenant={tenant}
            onSubmit={handleSubmit}
            isLoading={submitting}
            apiError={submitError}
          />
        ) : null}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], paddingBottom: spacing[12] },
})
