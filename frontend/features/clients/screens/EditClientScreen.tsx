import React from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { clientsApi } from '../api'
import { ClientForm } from '../components/ClientForm'
import { formValuesToUpdateClientInput } from '../form'
import { useClient } from '../hooks/useClient'
import type { ClientFormValues } from '../types'

export function EditClientScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { client, loading, error } = useClient(id ?? null)

  const {
    submitting,
    error: submitError,
    submit,
  } = useFormSubmit(async (values: ClientFormValues) => {
    if (!id) return
    const updated = await clientsApi.update(
      id,
      formValuesToUpdateClientInput(values),
      createIdempotencyKey('client_update'),
    )
    toast.success('Cliente actualizado')
    router.replace(Routes.tenant.clientDetail(updated.id) as Href)
  })

  if (loading) return <LoadingSpinner fullScreen label="Cargando cliente..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Editar cliente" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {error ? <ApiErrorBanner error={error} /> : null}
        {client ? (
          <ClientForm
            mode="edit"
            client={client}
            onSubmit={submit}
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
