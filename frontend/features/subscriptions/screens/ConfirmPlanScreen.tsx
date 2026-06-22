import React, { useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { Routes } from '@/constants/routes'
import { layout, overlay, radius, shadow, spacing, typography } from '@/constants/tokens'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useIsDesktopLayout } from '@/lib/hooks/useIsDesktopLayout'
import { useTheme } from '@/lib/theme-context'
import { formatCurrency } from '@/lib/utils/format'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { formatPlanLimit, isUnlimitedLimit } from '@/features/plans/format'
import { usePlans } from '@/features/plans/hooks/usePlans'
import type { LimitCycle, Plan } from '@/features/plans/types'
import { useTenant } from '@/features/tenants/hooks/useTenant'
import { tenantsApi } from '@/features/tenants/api'

const MAX_GRID_WIDTH = layout.contentMaxWidth
const DESKTOP_COLUMNS = 3

const BILLING_CYCLE_OPTIONS = [
  { value: 'month' as const, label: 'Mensual' },
  { value: 'year' as const, label: 'Anual' },
]

function isFreePlan(plan: Pick<Plan, 'monthly_price' | 'annual_price'>): boolean {
  return Number(plan.monthly_price) === 0 && Number(plan.annual_price) === 0
}

interface PlanOptionCardProps {
  plan: Plan
  billingCycle: LimitCycle
  selected: boolean
  current: boolean
  onSelect: () => void
}

function PlanOptionCard({ plan, billingCycle, selected, current, onSelect }: PlanOptionCardProps) {
  const { semantic } = useTheme()
  const borderColor = selected ? semantic.accent.default : semantic.border.default
  const indicatorBg = selected ? semantic.accent.default : semantic.bg.secondary
  const indicatorBorder = selected ? semantic.accent.default : semantic.border.strong
  const price = formatCurrency(billingCycle === 'year' ? plan.annual_price : plan.monthly_price)

  const meta = [
    {
      icon: 'document-text-outline' as const,
      label: isUnlimitedLimit(plan.document_limit)
        ? 'Docs ilimitados'
        : `${plan.document_limit.toLocaleString('es-EC')} docs`,
    },
    {
      icon: 'people-outline' as const,
      label: formatPlanLimit(plan.max_users, 'usuario', 'usuarios'),
    },
    {
      icon: 'business-outline' as const,
      label: formatPlanLimit(plan.max_locations, 'local', 'locales'),
    },
  ]

  const included = [
    'Todo en facturación',
    plan.includes_credit_notes ? 'Notas de crédito' : null,
    plan.includes_withholdings ? 'Retenciones' : null,
    plan.includes_delivery_notes ? 'Guías de remisión' : null,
    plan.includes_api ? 'API' : null,
  ].filter((label): label is string => Boolean(label))

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onSelect}
      style={({ pressed }) => [
        styles.planCard,
        selected ? shadow.md : shadow.sm,
        {
          backgroundColor: semantic.bg.elevated,
          borderColor,
          borderWidth: selected ? 2 : 1,
          opacity: pressed ? 0.92 : 1,
        },
      ]}
    >
      <View style={styles.planTopRow}>
        <View style={[styles.planIcon, { backgroundColor: semantic.accent.subtle }]}>
          <Ionicons name="pricetag-outline" size={18} color={semantic.accent.default} />
        </View>
        <View
          style={[
            styles.selectionIndicator,
            { backgroundColor: indicatorBg, borderColor: indicatorBorder },
          ]}
        >
          {selected ? <Ionicons name="checkmark" size={15} color={overlay.text.primary} /> : null}
        </View>
      </View>

      <View style={styles.planHeader}>
        <View style={styles.nameRow}>
          <Text style={[styles.planName, { color: semantic.text.primary }]}>{plan.name}</Text>
          {current ? (
            <View
              style={[
                styles.currentBadge,
                { backgroundColor: semantic.accent.subtle, borderColor: semantic.accent.muted },
              ]}
            >
              <Text style={[styles.currentBadgeText, { color: semantic.accent.default }]}>
                Actual
              </Text>
            </View>
          ) : null}
        </View>
        <Text
          style={[styles.planDescription, { color: semantic.text.secondary }]}
          numberOfLines={2}
        >
          {plan.description}
        </Text>
      </View>

      <View style={styles.priceRow}>
        <Text style={[styles.price, { color: semantic.text.primary }]}>{price}</Text>
        <Text style={[styles.priceCycle, { color: semantic.text.secondary }]}>
          {billingCycle === 'year' ? 'Anual' : 'Mensual'}
        </Text>
      </View>

      <View style={styles.metaGrid}>
        {meta.map((item) => (
          <View
            key={item.icon}
            style={[
              styles.metaPill,
              { backgroundColor: semantic.bg.secondary, borderColor: semantic.border.default },
            ]}
          >
            <Ionicons name={item.icon} size={14} color={semantic.text.secondary} />
            <Text style={[styles.metaText, { color: semantic.text.secondary }]} numberOfLines={1}>
              {item.label}
            </Text>
          </View>
        ))}
      </View>

      <View style={[styles.divider, { backgroundColor: semantic.border.default }]} />

      <View style={styles.includedWrap}>
        {included.slice(0, 4).map((label) => (
          <View key={label} style={styles.includedItem}>
            <Ionicons name="checkmark-circle" size={15} color={semantic.status.success} />
            <Text style={[styles.includedText, { color: semantic.text.primary }]}>{label}</Text>
          </View>
        ))}
      </View>
    </Pressable>
  )
}

export function ConfirmPlanScreen() {
  const { semantic } = useTheme()
  const isDesktop = useIsDesktopLayout()
  const router = useRouter()
  const user = useAuthStore(selectUser)
  const tenantId = user?.tenantId ?? null
  const { tenant, loading: tenantLoading } = useTenant(tenantId)
  const { plans, loading: plansLoading, error: plansError, refresh } = usePlans()
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null)
  const [selectedBillingCycle, setSelectedBillingCycle] = useState<LimitCycle>('year')
  const [idempotencyKey] = useState(() => createIdempotencyKey('subscription-confirm-plan'))
  const columns = isDesktop ? DESKTOP_COLUMNS : 1

  const selfServicePlans = plans.filter((plan) => plan.self_service)
  const currentBillingCycle = selectedBillingCycle
  const visiblePlans = selfServicePlans.filter(
    (plan) => currentBillingCycle !== 'month' || !isFreePlan(plan),
  )
  const requestedPlanId = selectedPlanId ?? tenant?.plan_id ?? null
  const currentPlan = visiblePlans.find((plan) => plan.id === requestedPlanId)
  const currentPlanId = currentPlan?.id ?? null

  const { submitting, error, submit } = useFormSubmit(async () => {
    if (!tenantId || !currentPlanId) return
    const updated = await tenantsApi.changePlan(
      tenantId,
      { plan_id: currentPlanId, billing_cycle: currentBillingCycle },
      idempotencyKey,
    )
    if (updated.subscription_status === 'pending_payment') {
      router.replace(Routes.app.activateSubscription as Href)
      return
    }
    router.replace(Routes.app.uploadCertificate as Href)
  })

  if (tenantLoading || plansLoading) return <LoadingSpinner fullScreen label="Cargando..." />
  if (!tenant) return null

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          <View style={styles.header}>
            <View style={styles.kickerRow}>
              <View style={[styles.kickerIcon, { backgroundColor: semantic.accent.subtle }]}>
                <Ionicons
                  name="shield-checkmark-outline"
                  size={16}
                  color={semantic.accent.default}
                />
              </View>
              <Text style={[styles.kicker, { color: semantic.accent.default }]}>Paso 1 de 2</Text>
            </View>
            <View style={styles.headerCopy}>
              <Text style={[styles.title, { color: semantic.text.primary }]}>Confirma tu plan</Text>
              <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
                Mantén tu plan actual o cambia a otro plan self-service antes de continuar.
              </Text>
            </View>
            <View style={styles.toggleWrap}>
              <SegmentedControl
                options={BILLING_CYCLE_OPTIONS}
                value={currentBillingCycle}
                onChange={setSelectedBillingCycle}
              />
            </View>
          </View>

          {plansError ? (
            <EmptyState
              icon="pricetags-outline"
              title="No pudimos cargar los planes"
              description="Intenta nuevamente para confirmar tu plan."
              action={{ label: 'Reintentar', onPress: refresh }}
            />
          ) : visiblePlans.length === 0 ? (
            <EmptyState
              icon="pricetags-outline"
              title="Sin planes disponibles"
              description="No hay planes self-service activos para continuar."
              action={{ label: 'Reintentar', onPress: refresh }}
            />
          ) : (
            <View style={styles.grid}>
              {visiblePlans.map((plan) => (
                <View
                  key={plan.id}
                  style={isDesktop ? styles.desktopCardWrap : styles.mobileCardWrap}
                >
                  <PlanOptionCard
                    plan={plan}
                    billingCycle={currentBillingCycle}
                    selected={plan.id === currentPlanId}
                    current={plan.id === tenant.plan_id}
                    onSelect={() => setSelectedPlanId(plan.id)}
                  />
                </View>
              ))}
            </View>
          )}

          {error ? <ApiErrorBanner error={error} /> : null}

          <View
            style={[
              styles.actionBar,
              columns === 1 ? styles.actionBarStacked : null,
              { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
            ]}
          >
            <View style={styles.selectionSummary}>
              <Text style={[styles.summaryLabel, { color: semantic.text.secondary }]}>
                Plan seleccionado
              </Text>
              <Text style={[styles.summaryValue, { color: semantic.text.primary }]}>
                {currentPlan
                  ? `${currentPlan.name} · ${currentBillingCycle === 'year' ? 'Anual' : 'Mensual'}`
                  : 'Selecciona un plan'}
              </Text>
            </View>
            <Button
              variant="primary"
              size="lg"
              fullWidth={columns === 1}
              isLoading={submitting}
              isDisabled={!currentPlanId || !!plansError || visiblePlans.length === 0}
              onPress={() => submit()}
              style={columns === 1 ? null : styles.continueButton}
            >
              Continuar
            </Button>
          </View>
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: {
    alignItems: 'center',
    padding: spacing[5],
    paddingBottom: spacing[12],
  },
  content: { gap: spacing[5], maxWidth: MAX_GRID_WIDTH, width: '100%' },
  header: { gap: spacing[4] },
  kickerRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  kickerIcon: {
    alignItems: 'center',
    borderRadius: radius.full,
    height: 28,
    justifyContent: 'center',
    width: 28,
  },
  kicker: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  headerCopy: { gap: spacing[2], maxWidth: 680 },
  title: {
    fontSize: typography.size['3xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['3xl'] * typography.lineHeight.tight,
  },
  subtitle: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.normal,
  },
  toggleWrap: { alignSelf: 'flex-start' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  desktopCardWrap: { width: '31%' },
  mobileCardWrap: { width: '100%' },
  planCard: {
    borderRadius: radius.md,
    gap: spacing[4],
    height: 420,
    padding: spacing[5],
  },
  planTopRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  planIcon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  selectionIndicator: {
    alignItems: 'center',
    borderRadius: radius.full,
    borderWidth: 1,
    height: 24,
    justifyContent: 'center',
    width: 24,
  },
  planHeader: { gap: spacing[1], minHeight: 70 },
  nameRow: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  planName: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    lineHeight: typography.size.xl * typography.lineHeight.tight,
  },
  currentBadge: {
    borderRadius: radius.full,
    borderWidth: 1,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1],
  },
  currentBadgeText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
  },
  planDescription: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
  priceRow: { gap: spacing[1] },
  price: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['2xl'] * typography.lineHeight.tight,
  },
  priceCycle: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  metaGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  metaPill: {
    alignItems: 'center',
    borderRadius: radius.full,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[1],
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1],
  },
  metaText: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  divider: { height: 1 },
  includedWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2], minHeight: 70 },
  includedItem: { alignItems: 'center', flexDirection: 'row', gap: spacing[1] },
  includedText: { fontSize: typography.size.sm },
  actionBar: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[4],
    justifyContent: 'space-between',
    padding: spacing[4],
  },
  actionBarStacked: { alignItems: 'stretch', flexDirection: 'column' },
  selectionSummary: { flex: 1, gap: spacing[1], minWidth: 0 },
  summaryLabel: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  summaryValue: {
    fontSize: typography.size.base,
    fontWeight: typography.weight.bold,
    lineHeight: typography.size.base * typography.lineHeight.tight,
  },
  continueButton: { minWidth: 180 },
})
