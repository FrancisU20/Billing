import React from 'react'
import { FlatList, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing, radius, shadow } from '@/constants/tokens'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { PlanCard } from '../components/PlanCard'
import { usePlans } from '../hooks/usePlans'

const pricingSignals = [
  { icon: 'flash-outline', label: 'SRI listo' },
  { icon: 'card-outline', label: 'Mensual' },
  { icon: 'business-outline', label: 'Escalable' },
] as const

export function PricingScreen() {
  const { plans, loading, error, refresh } = usePlans()
  const { semantic } = useTheme()
  const highlightedIndex = plans.length > 1 ? 1 : 0

  if (loading) return <LoadingSpinner fullScreen label="Cargando planes..." />

  return (
    <View style={[staticStyles.container, { backgroundColor: semantic.bg.page }]}>
      <View
        style={[
          staticStyles.hero,
          { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
        ]}
      >
        <View
          style={[
            staticStyles.heroBadge,
            { backgroundColor: semantic.accent.altSubtle, borderColor: semantic.border.default },
          ]}
        >
          <Ionicons name="sparkles-outline" size={14} color={semantic.accent.alt} />
          <Text style={[staticStyles.heroBadgeText, { color: semantic.accent.alt }]}>Planes</Text>
        </View>

        <View style={staticStyles.heroCopy}>
          <Text style={[staticStyles.title, { color: semantic.text.primary }]}>
            Facturación electrónica SRI
          </Text>
          <Text style={[staticStyles.subtitle, { color: semantic.text.secondary }]}>
            Elige una base clara para emitir documentos, crecer por usuarios y activar módulos
            cuando tu operación lo requiera.
          </Text>
        </View>

        <View style={staticStyles.signalRow}>
          {pricingSignals.map((signal) => (
            <View
              key={signal.label}
              style={[
                staticStyles.signalPill,
                { backgroundColor: semantic.bg.muted, borderColor: semantic.border.default },
              ]}
            >
              <Ionicons name={signal.icon} size={14} color={semantic.accent.tertiary} />
              <Text style={[staticStyles.signalText, { color: semantic.text.secondary }]}>
                {signal.label}
              </Text>
            </View>
          ))}
        </View>
      </View>

      {error ? (
        <View style={staticStyles.errorWrap}>
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
          renderItem={({ item, index }) => (
            <PlanCard plan={item} highlighted={index === highlightedIndex} />
          )}
          contentContainerStyle={staticStyles.list}
          ItemSeparatorComponent={() => <View style={{ height: spacing[4] }} />}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  )
}

const staticStyles = StyleSheet.create({
  container: { flex: 1 },
  hero: {
    margin: spacing[5],
    borderRadius: radius['2xl'],
    borderWidth: 1,
    padding: spacing[6],
    paddingTop: spacing[8],
    gap: spacing[5],
    ...shadow.lg,
  },
  heroBadge: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    borderWidth: 1,
    borderRadius: radius.full,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2] - 2,
  },
  heroBadgeText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  heroCopy: { gap: spacing[3] },
  title: {
    fontSize: typography.size['3xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['3xl'] * typography.lineHeight.tight,
  },
  subtitle: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.normal,
  },
  signalRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  signalPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    borderWidth: 1,
    borderRadius: radius.full,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2] - 1,
  },
  signalText: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  errorWrap: { paddingHorizontal: spacing[5], paddingBottom: spacing[5] },
  list: { paddingHorizontal: spacing[5], paddingBottom: spacing[10] },
})
