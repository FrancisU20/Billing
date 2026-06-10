import React, { useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { formatDate, formatRuc, initials } from '@/lib/utils/format'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { tenantsApi } from '../api'
import { TenantStatusBadge } from '../components/TenantStatusBadge'
import { TENANT_ENVIRONMENT_LABELS, TENANT_PLAN_STATUS_LABELS } from '../constants'
import { useTenant } from '../hooks/useTenant'
import type { Tenant } from '../types'

export function TenantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { tenant, loading, error, refresh } = useTenant(id ?? null)
  const [actionPending, setActionPending] = useState(false)
  const [actionError, setActionError] = useState<ApiError | null>(null)
  const [suspendOpen, setSuspendOpen] = useState(false)
  const [inactivateOpen, setInactivateOpen] = useState(false)
  const [reactivateOpen, setReactivateOpen] = useState(false)

  async function changeStatus(status: 'active' | 'suspended' | 'inactive') {
    if (!id) return
    setActionPending(true)
    setActionError(null)
    try {
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
    } catch (e) {
      setActionError(toApiError(e))
    } finally {
      setActionPending(false)
    }
  }

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
                      <SmallBadge label={TENANT_ENVIRONMENT_LABELS[tenant.sri_environment]} />
                      <SmallBadge label={TENANT_PLAN_STATUS_LABELS[tenant.plan_status]} />
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

                <DetailSection title="Información fiscal" icon="card-outline">
                  <Field label="RUC" value={formatRuc(tenant.ruc)} mono />
                  <Field
                    label="Entorno SRI"
                    value={TENANT_ENVIRONMENT_LABELS[tenant.sri_environment]}
                  />
                  <Field
                    label="Estado plan"
                    value={TENANT_PLAN_STATUS_LABELS[tenant.plan_status]}
                  />
                  <Field label="Plan ID" value={tenant.plan_id} mono />
                </DetailSection>

                <DetailSection title="Contacto" icon="mail-outline">
                  <Field label="Email" value={tenant.email} />
                  <Field label="Teléfono" value={tenant.phone} />
                  <Field label="Dirección" value={tenant.address} />
                  <Field label="Creado" value={formatDate(tenant.created_at)} />
                  <Field label="Actualizado" value={formatDate(tenant.updated_at)} />
                </DetailSection>

                <StatusSection
                  tenant={tenant}
                  actionPending={actionPending}
                  onSuspend={() => setSuspendOpen(true)}
                  onInactivate={() => setInactivateOpen(true)}
                  onReactivate={() => setReactivateOpen(true)}
                />
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
    </View>
  )
}

function StatusSection({
  tenant,
  actionPending,
  onSuspend,
  onInactivate,
  onReactivate,
}: {
  tenant: Tenant
  actionPending: boolean
  onSuspend: () => void
  onInactivate: () => void
  onReactivate: () => void
}) {
  const { semantic } = useTheme()
  const { status } = tenant

  return (
    <View
      style={[
        styles.section,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.sectionTitleRow}>
        <Ionicons name="shield-outline" size={17} color={semantic.accent.default} />
        <Text style={[styles.sectionTitle, { color: semantic.text.primary }]}>
          Gestión de estado
        </Text>
      </View>

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
          <Button
            variant="primary"
            size="md"
            fullWidth
            isDisabled={actionPending}
            onPress={onReactivate}
          >
            Reactivar empresa
          </Button>
        </>
      ) : (
        <>
          {status === 'active' ? (
            <>
              <Text style={[styles.statusDescription, { color: semantic.text.secondary }]}>
                La empresa está activa y puede emitir comprobantes electrónicos.
              </Text>
              <Button
                variant="warning"
                size="md"
                fullWidth
                isDisabled={actionPending}
                onPress={onSuspend}
              >
                Suspender empresa
              </Button>
            </>
          ) : (
            <>
              <Text style={[styles.statusDescription, { color: semantic.text.secondary }]}>
                La empresa está suspendida temporalmente y no puede emitir comprobantes.
              </Text>
              <Button
                variant="primary"
                size="md"
                fullWidth
                isDisabled={actionPending}
                onPress={onReactivate}
              >
                Reactivar empresa
              </Button>
            </>
          )}

          <View style={[styles.separator, { borderTopColor: semantic.border.default }]} />

          <View style={styles.dangerBlock}>
            <Button
              variant="danger"
              size="md"
              fullWidth
              isDisabled={actionPending}
              onPress={onInactivate}
            >
              Inactivar empresa
            </Button>
            <View style={styles.irreversibleNote}>
              <Ionicons name="ban-outline" size={12} color={semantic.status.error} />
              <Text style={[styles.irreversibleText, { color: semantic.status.error }]}>
                Sus datos se conservarán para auditoría fiscal
              </Text>
            </View>
          </View>
        </>
      )}
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
    height: sizes.avatarLg,
    justifyContent: 'center',
    width: sizes.avatarLg,
  },
  avatarText: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  profileCopy: { flex: 1, minWidth: 220, gap: spacing[1] },
  name: { fontSize: typography.size.xl, fontWeight: typography.weight.bold },
  subtle: { fontSize: typography.size.sm },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2], marginTop: spacing[1] },
  smallBadge: { borderRadius: radius.full, paddingHorizontal: spacing[2], paddingVertical: 2 },
  smallBadgeText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  profileActions: { flexDirection: 'row', gap: spacing[2] },
  section: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    padding: spacing[5],
  },
  sectionTitleRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  sectionTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  fieldGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  field: { flex: 1, minWidth: 220, gap: spacing[1] },
  fieldLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  fieldValue: { fontSize: typography.size.base },
  mono: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.sm },
  statusCurrentRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  statusCurrentLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  statusDescription: { fontSize: typography.size.sm, lineHeight: typography.size.sm * 1.6 },
  separator: { borderTopWidth: 1 },
  dangerBlock: { gap: spacing[2] },
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
