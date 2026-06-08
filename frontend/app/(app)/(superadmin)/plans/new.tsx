import React, { useState } from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { PlanForm } from '@/features/plans/components/PlanForm'
import { plansApi } from '@/features/plans/api'
import { useTheme } from '@/lib/theme-context'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useToast } from '@/components/feedback/Toast'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import type { CreatePlanInput, UpdatePlanInput } from '@/features/plans/types'

export default function NewPlanScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  async function handleSubmit(values: CreatePlanInput | UpdatePlanInput) {
    setSubmitting(true)
    setError(null)
    try {
      await plansApi.create(values as CreatePlanInput, createIdempotencyKey('plan_create'))
      toast.success('Plan creado')
      router.replace(Routes.superadmin.plans)
    } catch (e) {
      setError(toApiError(e))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Nuevo plan" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <PlanForm mode="create" onSubmit={handleSubmit} isLoading={submitting} apiError={error} />
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], paddingBottom: spacing[12] },
})
