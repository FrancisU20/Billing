import React, { useState } from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { clientsApi } from '../api'
import { ClientForm } from '../components/ClientForm'
import { formValuesToCreateClientInput } from '../form'
import type { ClientFormValues } from '../types'

export function NewClientScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  async function handleSubmit(values: ClientFormValues) {
    setSubmitting(true)
    setError(null)
    try {
      const client = await clientsApi.create(
        formValuesToCreateClientInput(values),
        createIdempotencyKey('client_create'),
      )
      toast.success('Cliente creado')
      router.replace(Routes.tenant.clientDetail(client.id) as Href)
    } catch (e) {
      setError(toApiError(e))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Nuevo cliente" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <ClientForm mode="create" onSubmit={handleSubmit} isLoading={submitting} apiError={error} />
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], paddingBottom: spacing[12] },
})
