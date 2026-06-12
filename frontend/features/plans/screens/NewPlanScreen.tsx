import React from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { plansApi } from '../api'
import { PlanForm } from '../components/PlanForm'
import type { CreatePlanInput, UpdatePlanInput } from '../types'

export function NewPlanScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()

  const { submitting, error, submit } = useFormSubmit(
    async (values: CreatePlanInput | UpdatePlanInput) => {
      await plansApi.create(values as CreatePlanInput, createIdempotencyKey('plan_create'))
      toast.success('Plan creado')
      router.replace(Routes.superadmin.plans)
    },
  )

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Nuevo plan" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <PlanForm mode="create" onSubmit={submit} isLoading={submitting} apiError={error} />
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], paddingBottom: spacing[12] },
})
