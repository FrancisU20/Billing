import React, { useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { Badge } from '@/components/ui/Badge'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { DetailField, DetailSection } from '@/components/ui/DetailSection'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { formatCurrency, formatDateTime } from '@/lib/utils/format'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { plansApi } from '../api'
import { PLAN_FEATURES } from '../constants'
import { cycleLabel, formatDocumentLimit, formatPlanLimit } from '../format'
import { useAdminPlan } from '../hooks/usePlan'

export function PlanDetailScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { plan, loading, error, refresh } = useAdminPlan(slug ?? null)
  const [confirmOpen, setConfirmOpen] = useState(false)

  useRefreshOnFocus(refresh)

  const {
    submitting: toggling,
    error: actionError,
    submit: confirmToggle,
  } = useFormSubmit(async () => {
    if (!plan) return
    await plansApi.setStatus(plan.id, !plan.active, createIdempotencyKey('plan_status'))
    toast.success(plan.active ? 'Plan desactivado' : 'Plan activado')
    router.replace(Routes.superadmin.plans)
  })

  if (loading) return <LoadingSpinner fullScreen label="Cargando plan..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title={plan?.name ?? 'Plan'} canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {error ? (
          <EmptyState
            icon="alert-circle-outline"
            title="No se pudo cargar el plan"
            description={error.message}
            action={{ label: 'Reintentar', onPress: refresh }}
          />
        ) : (
          <>
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
                      <Badge variant="accent" size="sm" label={cycleLabel(plan.limit_cycle)} />
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
                  <DetailField label="Mensual" value={formatCurrency(plan.monthly_price)} />
                  <DetailField label="Anual" value={formatCurrency(plan.annual_price)} />
                  <DetailField label="Orden" value={String(plan.order)} />
                  <DetailField label="Slug" value={plan.slug} mono />
                </DetailSection>

                <DetailSection title="Límites" icon="speedometer-outline">
                  <DetailField label="Documentos" value={formatDocumentLimit(plan)} />
                  <DetailField
                    label="Usuarios"
                    value={formatPlanLimit(plan.max_users, 'usuario', 'usuarios')}
                  />
                  <DetailField
                    label="Locales"
                    value={formatPlanLimit(plan.max_locations, 'local', 'locales')}
                  />
                  <DetailField
                    label="Puntos emisión"
                    value={formatPlanLimit(plan.max_emission_points, 'punto', 'puntos')}
                  />
                </DetailSection>

                <DetailSection title="Onboarding y entorno de pruebas" icon="flask-outline">
                  <DetailField
                    label="Documentos/mes en pruebas"
                    value={formatPlanLimit(
                      plan.pruebas_monthly_docs_limit,
                      'documento',
                      'documentos',
                    )}
                  />
                  <DetailField
                    label="Documentos batch/mes en pruebas"
                    value={formatPlanLimit(
                      plan.pruebas_monthly_bulk_limit,
                      'documento',
                      'documentos',
                    )}
                  />
                  <DetailField label="Queue dedicada" value={plan.dedicated_queue ? 'Sí' : 'No'} />
                  <DetailField
                    label="Onboarding self-service"
                    value={plan.self_service ? 'Sí' : 'No'}
                  />
                </DetailSection>

                <DetailSection title="Módulos" icon="apps-outline">
                  {PLAN_FEATURES.map((feature) => (
                    <DetailField
                      key={feature.key}
                      label={feature.label}
                      value={plan[feature.key] ? 'Incluido' : 'No incluido'}
                    />
                  ))}
                </DetailSection>

                <DetailSection title="Metadata" icon="time-outline">
                  <DetailField label="Creado" value={formatDateTime(plan.created_at)} />
                  <DetailField label="Actualizado" value={formatDateTime(plan.updated_at)} />
                  <DetailField label="ID" value={plan.id} mono />
                </DetailSection>
              </>
            ) : null}
          </>
        )}
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
    height: sizes.avatarLg,
    justifyContent: 'center',
    width: sizes.avatarLg,
  },
  profileCopy: { flex: 1, gap: spacing[1], minWidth: 220 },
  name: { fontSize: typography.size.xl, fontWeight: typography.weight.bold },
  subtle: { fontSize: typography.size.sm },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2], marginTop: spacing[1] },
  profileActions: { flexDirection: 'row', gap: spacing[2] },
})
