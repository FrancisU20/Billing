import React, { useState } from 'react'
import { ScrollView, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { DetailField, DetailSection } from '@/components/ui/DetailSection'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { formatDateTime, formatRuc, initials } from '@/lib/utils/format'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { tenantsApi } from '../api'
import { CertificateSection } from '../components/CertificateSection'
import { TenantStatusBadge } from '../components/TenantStatusBadge'
import {
  TENANT_ENVIRONMENT_BADGE_VARIANT,
  TENANT_ENVIRONMENT_LABELS,
  TENANT_PLAN_STATUS_LABELS,
} from '../constants'
import { useTenant } from '../hooks/useTenant'
import type { Tenant } from '../types'

export function TenantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { tenant, loading, error, refresh } = useTenant(id ?? null)
  const [suspendOpen, setSuspendOpen] = useState(false)
  const [inactivateOpen, setInactivateOpen] = useState(false)
  const [reactivateOpen, setReactivateOpen] = useState(false)
  const [retryOnboardingOpen, setRetryOnboardingOpen] = useState(false)

  useRefreshOnFocus(refresh)

  const {
    submitting: actionPending,
    error: actionError,
    submit: changeStatus,
  } = useFormSubmit(async (status: 'active' | 'suspended' | 'inactive') => {
    if (!id) return
    await tenantsApi.setStatus(id, status, createIdempotencyKey(`tenant_status_${status}`))
    setSuspendOpen(false)
    setInactivateOpen(false)
    setReactivateOpen(false)
    const label =
      status === 'active'
        ? 'Empresa reactivada'
        : status === 'suspended'
          ? 'Empresa suspendida'
          : 'Empresa inactivada'
    toast.success(label)
    await refresh()
  })

  const {
    submitting: retryOnboardingPending,
    error: retryOnboardingError,
    submit: retryOnboarding,
  } = useFormSubmit(async () => {
    if (!id) return
    await tenantsApi.retryOnboarding(id, createIdempotencyKey('tenant_onboarding_retry'))
    setRetryOnboardingOpen(false)
    toast.success('Acceso inicial encolado')
  })

  if (loading) return <LoadingSpinner fullScreen label="Cargando empresa..." />

  const displayName = tenant?.trade_name ?? 'Empresa'

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title={displayName} canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {error ? (
          <EmptyState
            icon="alert-circle-outline"
            title="No se pudo cargar la empresa"
            description={error.message}
            action={{ label: 'Reintentar', onPress: refresh }}
          />
        ) : (
          <>
            {actionError ? <ApiErrorBanner error={actionError} /> : null}
            {retryOnboardingError ? <ApiErrorBanner error={retryOnboardingError} /> : null}

            {tenant ? (
              <>
                <View
                  style={[
                    styles.profile,
                    { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
                  ]}
                >
                  <View style={[styles.avatar, { backgroundColor: semantic.accent.subtle }]}>
                    <Text style={[styles.avatarText, { color: semantic.accent.default }]}>
                      {initials(displayName)}
                    </Text>
                  </View>
                  <View style={styles.profileCopy}>
                    <Text style={[styles.name, { color: semantic.text.primary }]}>
                      {displayName}
                    </Text>
                    <Text style={[styles.subtle, { color: semantic.text.secondary }]}>
                      {tenant.legal_rep_name}
                    </Text>
                    <View style={styles.badgeRow}>
                      <TenantStatusBadge status={tenant.status} />
                      <Badge
                        variant={TENANT_ENVIRONMENT_BADGE_VARIANT[tenant.sri_environment]}
                        size="sm"
                        label={TENANT_ENVIRONMENT_LABELS[tenant.sri_environment]}
                      />
                      <Badge
                        variant="accent"
                        size="sm"
                        label={TENANT_PLAN_STATUS_LABELS[tenant.plan_status]}
                      />
                    </View>
                  </View>
                  <View style={styles.profileActions}>
                    <Button
                      variant="outline"
                      size="sm"
                      onPress={() => router.push(Routes.superadmin.tenantEdit(tenant.id) as Href)}
                    >
                      Editar
                    </Button>
                  </View>
                </View>

                <View style={styles.infoGrid}>
                  <DetailSection
                    title="Información fiscal"
                    icon="card-outline"
                    style={styles.infoCard}
                  >
                    <DetailField label="RUC" value={formatRuc(tenant.ruc)} mono />
                    <DetailField label="Razón social" value={tenant.legal_name} />
                    <DetailField
                      label="Obligado a llevar contabilidad"
                      value={tenant.accounting_required ? 'Sí' : 'No'}
                    />
                    <DetailField
                      label="Entorno SRI"
                      value={TENANT_ENVIRONMENT_LABELS[tenant.sri_environment]}
                    />
                    <DetailField
                      label="Estado plan"
                      value={TENANT_PLAN_STATUS_LABELS[tenant.plan_status]}
                    />
                    <DetailField label="Plan ID" value={tenant.plan_id} mono />
                  </DetailSection>

                  <DetailSection title="Contacto" icon="mail-outline" style={styles.infoCard}>
                    <DetailField label="Email" value={tenant.email} />
                    <DetailField label="Teléfono" value={tenant.phone} />
                    <DetailField label="Dirección" value={tenant.address} />
                    <DetailField label="Creado" value={formatDateTime(tenant.created_at)} />
                    <DetailField label="Actualizado" value={formatDateTime(tenant.updated_at)} />
                  </DetailSection>
                </View>

                <View style={styles.operationsGrid}>
                  <CertificateSection
                    tenantId={tenant.id}
                    canManage
                    actionSize="md"
                    style={styles.operationCard}
                  />

                  <OwnerAccessSection
                    tenant={tenant}
                    actionPending={retryOnboardingPending}
                    onRetry={() => setRetryOnboardingOpen(true)}
                    style={styles.operationCard}
                  />

                  <StatusSection
                    tenant={tenant}
                    actionPending={actionPending}
                    onSuspend={() => setSuspendOpen(true)}
                    onInactivate={() => setInactivateOpen(true)}
                    onReactivate={() => setReactivateOpen(true)}
                    style={styles.operationCard}
                  />
                </View>
              </>
            ) : null}
          </>
        )}
      </ScrollView>

      <ConfirmDialog
        visible={suspendOpen}
        variant="warning"
        icon="pause-circle-outline"
        title="Suspender empresa"
        message={`${displayName} quedará bloqueada temporalmente. No podrá emitir comprobantes hasta ser reactivada.`}
        confirmLabel="Suspender"
        isLoading={actionPending}
        onCancel={() => setSuspendOpen(false)}
        onConfirm={() => changeStatus('suspended')}
      />

      <ConfirmDialog
        visible={reactivateOpen}
        variant="success"
        icon="checkmark-circle-outline"
        title="Reactivar empresa"
        message={`${displayName} volverá a estar activa y podrá emitir comprobantes.`}
        confirmLabel="Reactivar"
        isLoading={actionPending}
        onCancel={() => setReactivateOpen(false)}
        onConfirm={() => changeStatus('active')}
      />

      <ConfirmDialog
        visible={inactivateOpen}
        variant="danger"
        icon="ban-outline"
        title="Inactivar empresa"
        message={`${displayName} quedará inactiva y no podrá emitir comprobantes hasta que un superadmin la reactive. Sus datos y comprobantes se conservan para efectos de auditoría fiscal.`}
        confirmLabel="Inactivar"
        isLoading={actionPending}
        onCancel={() => setInactivateOpen(false)}
        onConfirm={() => changeStatus('inactive')}
      />

      <ConfirmDialog
        visible={retryOnboardingOpen}
        variant="warning"
        icon="person-add-outline"
        title="Reintentar acceso owner"
        message={`Se encolará nuevamente el acceso inicial para ${tenant?.email ?? displayName}.`}
        confirmLabel="Reintentar"
        isLoading={retryOnboardingPending}
        onCancel={() => setRetryOnboardingOpen(false)}
        onConfirm={retryOnboarding}
      />
    </View>
  )
}

function OwnerAccessSection({
  tenant,
  actionPending,
  onRetry,
  style,
}: {
  tenant: Tenant
  actionPending: boolean
  onRetry: () => void
  style?: StyleProp<ViewStyle>
}) {
  return (
    <DetailSection
      title="Acceso owner"
      icon="person-add-outline"
      layout="stack"
      style={style}
      contentStyle={styles.operationContent}
    >
      <View style={styles.compactFields}>
        <DetailField label="Email owner" value={tenant.email} />
        <DetailField
          label="Onboarding completado"
          value={
            tenant.onboarding_completed_at ? formatDateTime(tenant.onboarding_completed_at) : '-'
          }
        />
      </View>
      <View style={styles.sectionActions}>
        <Button variant="outline" size="md" fullWidth isDisabled={actionPending} onPress={onRetry}>
          Reintentar acceso inicial
        </Button>
      </View>
    </DetailSection>
  )
}

function StatusSection({
  tenant,
  actionPending,
  onSuspend,
  onInactivate,
  onReactivate,
  style,
}: {
  tenant: Tenant
  actionPending: boolean
  onSuspend: () => void
  onInactivate: () => void
  onReactivate: () => void
  style?: StyleProp<ViewStyle>
}) {
  const { semantic } = useTheme()
  const { status } = tenant

  return (
    <DetailSection
      title="Gestión de estado"
      icon="shield-outline"
      layout="stack"
      style={style}
      contentStyle={styles.operationContent}
    >
      <View style={styles.statusCurrentRow}>
        <Text style={[styles.statusCurrentLabel, { color: semantic.text.secondary }]}>
          Estado actual:
        </Text>
        <TenantStatusBadge status={status} />
      </View>

      {status === 'inactive' ? (
        <>
          <View
            style={[
              styles.infoBanner,
              { backgroundColor: semantic.status.errorBg, borderColor: semantic.status.error },
            ]}
          >
            <Ionicons name="ban-outline" size={18} color={semantic.status.error} />
            <Text style={[styles.infoBannerText, { color: semantic.text.secondary }]}>
              Esta empresa está inactiva. No puede emitir comprobantes, pero puede reactivarse
              cuando el contrato vuelva a estar vigente.
            </Text>
          </View>
          <View style={styles.statusFooter}>
            <Button
              variant="primary"
              size="md"
              fullWidth
              isDisabled={actionPending}
              onPress={onReactivate}
            >
              Reactivar empresa
            </Button>
          </View>
        </>
      ) : (
        <>
          {status === 'active' ? (
            <Text style={[styles.statusDescription, { color: semantic.text.secondary }]}>
              La empresa está activa y puede emitir comprobantes electrónicos.
            </Text>
          ) : (
            <Text style={[styles.statusDescription, { color: semantic.text.secondary }]}>
              La empresa está suspendida temporalmente y no puede emitir comprobantes.
            </Text>
          )}

          <View style={styles.statusFooter}>
            <View style={styles.statusActionsRow}>
              {status === 'active' ? (
                <Button
                  variant="warningSubtle"
                  size="md"
                  fullWidth
                  isDisabled={actionPending}
                  onPress={onSuspend}
                >
                  Suspender empresa
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="md"
                  fullWidth
                  isDisabled={actionPending}
                  onPress={onReactivate}
                >
                  Reactivar empresa
                </Button>
              )}
              <Button
                variant="dangerSubtle"
                size="md"
                fullWidth
                isDisabled={actionPending}
                onPress={onInactivate}
              >
                Inactivar empresa
              </Button>
            </View>
            <View style={styles.irreversibleNote}>
              <Ionicons name="ban-outline" size={12} color={semantic.status.error} />
              <Text style={[styles.irreversibleText, { color: semantic.status.error }]}>
                Sus datos se conservarán para auditoría fiscal
              </Text>
            </View>
          </View>
        </>
      )}
    </DetailSection>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
  infoGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  infoCard: { flex: 1, minWidth: 280 },
  operationsGrid: {
    alignItems: 'stretch',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[4],
  },
  operationCard: { flex: 1, minWidth: 280 },
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
  avatarText: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  profileCopy: { flex: 1, minWidth: 220, gap: spacing[1] },
  name: { fontSize: typography.size.xl, fontWeight: typography.weight.bold },
  subtle: { fontSize: typography.size.sm },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2], marginTop: spacing[1] },
  profileActions: { flexDirection: 'row', gap: spacing[2] },
  operationContent: { flex: 1 },
  compactFields: { gap: spacing[4] },
  sectionActions: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginTop: 'auto',
    width: '100%',
  },
  statusCurrentRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  statusCurrentLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  statusDescription: { fontSize: typography.size.sm, lineHeight: typography.size.sm * 1.6 },
  statusFooter: { alignItems: 'center', gap: spacing[3], marginTop: 'auto', width: '100%' },
  statusActionsRow: { gap: spacing[2], width: '100%' },
  irreversibleNote: { alignItems: 'center', flexDirection: 'row', gap: spacing[1] },
  irreversibleText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.medium,
  },
  infoBanner: {
    alignItems: 'flex-start',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    padding: spacing[4],
  },
  infoBannerText: { flex: 1, fontSize: typography.size.sm, lineHeight: typography.size.sm * 1.6 },
})
