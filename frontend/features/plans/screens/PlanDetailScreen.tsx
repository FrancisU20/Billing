import React, { useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { Badge } from '@/components/ui/Badge'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { formatCurrency, formatDate } from '@/lib/utils/format'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'
import { plansApi } from '../api'
import { PLAN_FEATURES } from '../constants'
import { cycleLabel, formatDocumentLimit, formatPlanLimit } from '../format'
import { usePlan } from '../hooks/usePlan'

export function PlanDetailScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { plan, loading, error } = usePlan(slug ?? null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [toggling, setToggling] = useState(false)
  const [actionError, setActionError] = useState<ApiError | null>(null)

  async function confirmToggle() {
    if (!plan) return
    setToggling(true)
    setActionError(null)
    try {
      await plansApi.setStatus(plan.id, !plan.active, createIdempotencyKey('plan_status'))
      toast.success(plan.active ? 'Plan desactivado' : 'Plan activado')
      router.replace(Routes.superadmin.plans)
    } catch (e) {
      setActionError(toApiError(e))
    } finally {
      setToggling(false)
    }
  }

  if (loading) return <LoadingSpinner fullScreen label="Cargando plan..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title={plan?.name ?? 'Plan'} canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {error ? <ApiErrorBanner error={error} /> : null}
        {actionError ? <ApiErrorBanner error={actionError} /> : null}

        {plan ? (
          <>
            <View
              style={[
                styles.profile,
                { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
              ]}
            >
              <View style={[styles.avatar, { backgroundColor: semantic.accent.subtle }]}>
                <Ionicons name="pricetag-outline" size={24} color={semantic.accent.default} />
              </View>
              <View style={styles.profileCopy}>
                <Text style={[styles.name, { color: semantic.text.primary }]}>{plan.name}</Text>
                <Text style={[styles.subtle, { color: semantic.text.secondary }]}>
                  {plan.description || plan.slug}
                </Text>
                <View style={styles.badgeRow}>
                  <Badge
                    label={plan.active ? 'Activo' : 'Inactivo'}
                    variant={plan.active ? 'success' : 'neutral'}
                    size="sm"
                  />
                  <SmallBadge label={cycleLabel(plan.limit_cycle)} />
                </View>
              </View>
              <View style={styles.profileActions}>
                <Button
                  variant="outline"
                  size="sm"
                  onPress={() => router.push(Routes.superadmin.planEdit(plan.slug) as Href)}
                >
                  Editar
                </Button>
                <Button
                  variant={plan.active ? 'danger' : 'primary'}
                  size="sm"
                  onPress={() => setConfirmOpen(true)}
                >
                  {plan.active ? 'Desactivar' : 'Activar'}
                </Button>
              </View>
            </View>

            <DetailSection title="Precio" icon="cash-outline">
              <Field label="Mensual" value={formatCurrency(plan.monthly_price)} />
              <Field label="Anual" value={formatCurrency(plan.annual_price)} />
              <Field label="Orden" value={String(plan.order)} />
              <Field label="Slug" value={plan.slug} mono />
            </DetailSection>

            <DetailSection title="Límites" icon="speedometer-outline">
              <Field label="Documentos" value={formatDocumentLimit(plan)} />
              <Field
                label="Usuarios"
                value={formatPlanLimit(plan.max_users, 'usuario', 'usuarios')}
              />
              <Field
                label="Locales"
                value={formatPlanLimit(plan.max_locations, 'local', 'locales')}
              />
              <Field
                label="Puntos emisión"
                value={formatPlanLimit(plan.max_emission_points, 'punto', 'puntos')}
              />
            </DetailSection>

            <DetailSection title="Módulos" icon="apps-outline">
              {PLAN_FEATURES.map((feature) => (
                <Field
                  key={feature.key}
                  label={feature.label}
                  value={plan[feature.key] ? 'Incluido' : 'No incluido'}
                />
              ))}
            </DetailSection>

            <DetailSection title="Metadata" icon="time-outline">
              <Field label="Creado" value={formatDate(plan.created_at)} />
              <Field label="Actualizado" value={formatDate(plan.updated_at)} />
              <Field label="ID" value={plan.id} mono />
            </DetailSection>
          </>
        ) : null}
      </ScrollView>

      <ConfirmDialog
        visible={confirmOpen}
        title={plan?.active ? 'Desactivar plan' : 'Activar plan'}
        message={`El plan ${plan?.name ?? ''} ${plan?.active ? 'dejará de mostrarse como disponible.' : 'volverá a estar disponible.'}`}
        confirmLabel={plan?.active ? 'Desactivar' : 'Activar'}
        icon={plan?.active ? 'pause-circle-outline' : 'play-circle-outline'}
        isLoading={toggling}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={confirmToggle}
      />
    </View>
  )
}

function SmallBadge({ label }: { label: string }) {
  const { semantic } = useTheme()
  return (
    <View style={[styles.smallBadge, { backgroundColor: semantic.accent.altSubtle }]}>
      <Text style={[styles.smallBadgeText, { color: semantic.accent.alt }]}>{label}</Text>
    </View>
  )
}

function DetailSection({
  title,
  icon,
  children,
}: {
  title: string
  icon: keyof typeof Ionicons.glyphMap
  children: React.ReactNode
}) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.section,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.sectionTitleRow}>
        <Ionicons name={icon} size={17} color={semantic.accent.default} />
        <Text style={[styles.sectionTitle, { color: semantic.text.primary }]}>{title}</Text>
      </View>
      <View style={styles.fieldGrid}>{children}</View>
    </View>
  )
}

function Field({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.field}>
      <Text style={[styles.fieldLabel, { color: semantic.text.secondary }]}>{label}</Text>
      <Text
        style={[styles.fieldValue, mono && styles.mono, { color: semantic.text.primary }]}
        numberOfLines={2}
      >
        {value}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
  profile: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[4],
    padding: spacing[5],
  },
  avatar: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: 58,
    justifyContent: 'center',
    width: 58,
  },
  profileCopy: { flex: 1, gap: spacing[1], minWidth: 220 },
  name: { fontSize: typography.size.xl, fontWeight: typography.weight.bold },
  subtle: { fontSize: typography.size.sm },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2], marginTop: spacing[1] },
  smallBadge: { borderRadius: radius.full, paddingHorizontal: spacing[2], paddingVertical: 2 },
  smallBadgeText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  profileActions: { flexDirection: 'row', gap: spacing[2] },
  section: { borderRadius: radius.md, borderWidth: 1, gap: spacing[4], padding: spacing[5] },
  sectionTitleRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  sectionTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  fieldGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  field: { flex: 1, gap: spacing[1], minWidth: 220 },
  fieldLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  fieldValue: { fontSize: typography.size.base },
  mono: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.sm },
})
