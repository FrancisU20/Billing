import React, { forwardRef, useMemo, useState } from 'react'
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

const MAX_GRID_WIDTH = 1180
const THREE_COLUMN_MIN_WIDTH = 940
const TWO_COLUMN_MIN_WIDTH = 620

export const PlansSection = forwardRef<View, PlansSectionProps>(function PlansSection(
  { onLayout },
  ref,
) {
  const [sectionWidth, setSectionWidth] = useState(0)
  const { plans, loading, error, refresh } = usePlans()
  const { semantic } = useTheme()
  const router = useRouter()
  const selectPlan = useOnboardingStore((state) => state.selectPlan)
  const highlightedIndex = plans.length > 1 ? 1 : 0

  const gridWidth = Math.min(Math.max(sectionWidth - spacing[5] * 2, 0), MAX_GRID_WIDTH)
  const columns =
    gridWidth >= THREE_COLUMN_MIN_WIDTH ? 3 : gridWidth >= TWO_COLUMN_MIN_WIDTH ? 2 : 1
  const cardWidth = useMemo(() => {
    if (!gridWidth) return undefined
    const totalGap = spacing[4] * (columns - 1)
    return Math.floor((gridWidth - totalGap) / columns)
  }, [columns, gridWidth])

  const handleSelect = (plan: Plan) => {
    selectPlan(plan)
    router.push(Routes.public.registerDetails as Href)
  }

  const handleLayout = (event: LayoutChangeEvent) => {
    setSectionWidth(event.nativeEvent.layout.width)
    onLayout?.(event)
  }

  return (
    <View
      ref={ref}
      onLayout={handleLayout}
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
        <View style={[styles.grid, gridWidth ? { maxWidth: gridWidth } : null]}>
          {plans.map((plan, index) => (
            <View key={plan.id} style={[styles.cardWrap, cardWidth ? { width: cardWidth } : null]}>
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
  grid: {
    alignItems: 'stretch',
    alignSelf: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[4],
    justifyContent: 'center',
    width: '100%',
  },
  cardWrap: { alignSelf: 'stretch', borderRadius: radius.md },
})
