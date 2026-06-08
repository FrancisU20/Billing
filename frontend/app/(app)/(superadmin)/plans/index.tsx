import React from 'react'
import { FlatList, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { PlanCard } from '@/features/plans/components/PlanCard'
import { usePlans } from '@/features/plans/hooks/usePlans'

export default function PlansManagementScreen() {
  const { plans, loading, error, refresh } = usePlans()
  const { semantic } = useTheme()
  const activePlans = plans.filter((plan) => plan.active).length

  if (loading) return <LoadingSpinner fullScreen label="Cargando planes..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Planes" subtitle={`${plans.length} planes`} />

      {error ? (
        <View style={styles.errorWrap}>
          <ApiErrorBanner error={error} />
        </View>
      ) : (
        <FlatList
          data={plans}
          keyExtractor={(p) => p.id}
          renderItem={({ item }) => <PlanCard plan={item} />}
          contentContainerStyle={styles.list}
          ListHeaderComponentStyle={styles.listHeader}
          ListHeaderComponent={
            <View style={[styles.summary, { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default }]}>
              <View style={[styles.summaryIcon, { backgroundColor: semantic.accent.altSubtle }]}>
                <Ionicons name="layers-outline" size={20} color={semantic.accent.alt} />
              </View>
              <View style={styles.summaryCopy}>
                <Text style={[styles.summaryTitle, { color: semantic.text.primary }]}>Catálogo comercial</Text>
                <Text style={[styles.summarySubtitle, { color: semantic.text.secondary }]}>
                  {activePlans} activos de {plans.length} configurados
                </Text>
              </View>
            </View>
          }
          ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
          ListEmptyComponent={
            <EmptyState
              icon="pricetags-outline"
              title="Sin planes"
              description="No hay planes configurados."
            />
          }
          refreshing={loading}
          onRefresh={refresh}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  errorWrap: { padding: spacing[5] },
  list: { padding: spacing[4], paddingBottom: spacing[10] },
  listHeader: { marginBottom: spacing[3] },
  summary: { flexDirection: 'row', alignItems: 'center', gap: spacing[3], borderRadius: radius['2xl'], borderWidth: 1, padding: spacing[5] },
  summaryIcon: { width: 44, height: 44, borderRadius: radius.lg, alignItems: 'center', justifyContent: 'center' },
  summaryCopy: { flex: 1, minWidth: 0, gap: spacing[1] },
  summaryTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  summarySubtitle: { fontSize: typography.size.sm },
})
