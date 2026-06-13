import React, { forwardRef } from 'react'
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { PlanCard } from '@/features/plans/components/PlanCard'
import { usePlans } from '@/features/plans/hooks/usePlans'
import type { Plan } from '@/features/plans/types'
import { useOnboardingStore } from '@/features/onboarding/store'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'

interface PlansSectionProps {
  onLayout?: (event: LayoutChangeEvent) => void
}

export const PlansSection = forwardRef<View, PlansSectionProps>(function PlansSection(
  { onLayout },
  ref,
) {
  const { plans, loading, error, refresh } = usePlans()
  const { semantic } = useTheme()
  const router = useRouter()
  const selectPlan = useOnboardingStore((state) => state.selectPlan)
  const highlightedIndex = plans.length > 1 ? 1 : 0

  const handleSelect = (plan: Plan) => {
    selectPlan(plan)
    router.push(Routes.public.registerDetails as Href)
  }

  return (
    <View
      ref={ref}
      onLayout={onLayout}
      style={[styles.container, { backgroundColor: semantic.bg.tertiary }]}
    >
      <View style={styles.heading}>
        <Text style={[styles.title, { color: semantic.text.primary }]}>
          Elige tu plan y crea tu cuenta
        </Text>
        <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
          Sin contratos forzosos. Cambia o cancela tu plan cuando lo necesites.
        </Text>
      </View>

      {loading ? (
        <LoadingSpinner label="Cargando planes..." />
      ) : error ? (
        <ApiErrorBanner error={error} />
      ) : plans.length === 0 ? (
        <EmptyState
          icon="pricetags-outline"
          title="Sin planes disponibles"
          description="Vuelve pronto, estamos configurando los planes."
          action={{ label: 'Reintentar', onPress: refresh }}
        />
      ) : (
        <View style={styles.grid}>
          {plans.map((plan, index) => (
            <View key={plan.id} style={styles.cardWrap}>
              <PlanCard
                plan={plan}
                highlighted={index === highlightedIndex}
                onSelect={() => handleSelect(plan)}
              />
            </View>
          ))}
        </View>
      )}
    </View>
  )
})

const styles = StyleSheet.create({
  container: { gap: spacing[5], paddingHorizontal: spacing[5], paddingVertical: spacing[6] },
  heading: { gap: spacing[2] },
  title: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['2xl'] * typography.lineHeight.tight,
  },
  subtitle: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.normal,
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  cardWrap: { borderRadius: radius['2xl'], flexBasis: 300, flexGrow: 1 },
})
