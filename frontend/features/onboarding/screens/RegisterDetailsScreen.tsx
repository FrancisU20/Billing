import React, { useEffect } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { Routes } from '@/constants/routes'
import { spacing, typography } from '@/constants/tokens'
import { RegistrationForm } from '../components/RegistrationForm'
import { formValuesToOnboardingPayload } from '../form'
import { useRequestOtp } from '../hooks/useRequestOtp'
import { useOnboardingStore } from '../store'
import type { RegistrationFormValues } from '../schemas'

export function RegisterDetailsScreen() {
  const { semantic } = useTheme()
  const router = useRouter()
  const selectedPlan = useOnboardingStore((state) => state.selectedPlan)
  const selectedBillingCycle = useOnboardingStore((state) => state.selectedBillingCycle)
  const formValues = useOnboardingStore((state) => state.formValues)
  const setFormValues = useOnboardingStore((state) => state.setFormValues)
  const requestOtp = useRequestOtp()

  useEffect(() => {
    if (!selectedPlan) {
      router.replace(Routes.root as Href)
    }
  }, [selectedPlan, router])

  const { submitting, error, submit } = useFormSubmit(async (values: RegistrationFormValues) => {
    if (!selectedPlan) return
    setFormValues(values)
    await requestOtp(formValuesToOnboardingPayload(values, selectedPlan.id, selectedBillingCycle))
  })

  if (!selectedPlan) return null

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: semantic.text.primary }]}>Datos de tu empresa</Text>
        <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
          Plan seleccionado: {selectedPlan.name}
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <RegistrationForm
          defaultValues={formValues ?? undefined}
          onSubmit={submit}
          isLoading={submitting}
          apiError={error}
        />
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { gap: spacing[2], padding: spacing[5], paddingTop: spacing[8] },
  title: {
    fontSize: typography.size['3xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['3xl'] * typography.lineHeight.tight,
  },
  subtitle: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.normal,
  },
  scroll: { padding: spacing[5], paddingBottom: spacing[12] },
})
