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
import { plansApi } from '../api'
import { PlanForm } from '../components/PlanForm'
import { usePlan } from '../hooks/usePlan'
import type { CreatePlanInput, UpdatePlanInput } from '../types'

export function EditPlanScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { plan, loading, error } = usePlan(slug ?? null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<ApiError | null>(null)

  async function handleSubmit(values: CreatePlanInput | UpdatePlanInput) {
    if (!plan) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const updated = await plansApi.update(
        plan.id,
        values as UpdatePlanInput,
        createIdempotencyKey('plan_update'),
      )
      toast.success('Plan actualizado')
      router.replace(Routes.superadmin.planDetail(updated.slug) as Href)
    } catch (e) {
      setSubmitError(toApiError(e))
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <LoadingSpinner fullScreen label="Cargando plan..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Editar plan" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {error ? <ApiErrorBanner error={error} /> : null}
        {plan ? (
          <PlanForm
            mode="edit"
            plan={plan}
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
