import React from 'react'
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { PlanCard } from '@/features/plans/components/PlanCard'
import { usePlans } from '@/features/plans/hooks/usePlans'
import type { Plan } from '@/features/plans/types'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'
import { useOnboardingStore } from '../store'

export function RegisterPlanScreen() {
  const { plans, loading, error, refresh } = usePlans()
  const { semantic } = useTheme()
  const router = useRouter()
  const selectPlan = useOnboardingStore((state) => state.selectPlan)

  const handleSelect = (plan: Plan) => {
    selectPlan(plan)
    router.push(Routes.public.registerDetails as Href)
  }

  if (loading) return <LoadingSpinner fullScreen label="Cargando planes..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: semantic.text.primary }]}>Crea tu cuenta</Text>
        <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
          Elige el plan con el que quieres empezar a emitir documentos electrónicos.
        </Text>
      </View>

      {error ? (
        <View style={styles.errorWrap}>
          <ApiErrorBanner error={error} />
        </View>
      ) : plans.length === 0 ? (
        <EmptyState
          icon="pricetags-outline"
          title="Sin planes disponibles"
          description="Vuelve pronto, estamos configurando los planes."
          action={{ label: 'Reintentar', onPress: refresh }}
        />
      ) : (
        <FlatList
          data={plans}
          keyExtractor={(p) => p.id}
          renderItem={({ item }) => (
            <Pressable
              onPress={() => handleSelect(item)}
              style={({ pressed }) => [styles.cardWrap, pressed && styles.cardWrapPressed]}
            >
              <PlanCard plan={item} />
            </Pressable>
          )}
          contentContainerStyle={styles.list}
          ItemSeparatorComponent={() => <View style={{ height: spacing[4] }} />}
          showsVerticalScrollIndicator={false}
        />
      )}
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
  errorWrap: { paddingHorizontal: spacing[5], paddingBottom: spacing[5] },
  list: { paddingHorizontal: spacing[5], paddingBottom: spacing[10] },
  cardWrap: { borderRadius: radius['2xl'] },
  cardWrapPressed: { opacity: 0.85 },
})
