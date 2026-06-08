import React, { useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { formatDate, formatRuc, initials } from '@/lib/utils/format'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'
import { tenantsApi } from '../api'
import { TenantStatusBadge } from '../components/TenantStatusBadge'
import { TENANT_ENVIRONMENT_LABELS, TENANT_PLAN_STATUS_LABELS } from '../constants'
import { useTenant } from '../hooks/useTenant'

export function TenantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { tenant, loading, error } = useTenant(id ?? null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState<ApiError | null>(null)

  async function confirmDelete() {
    if (!id) return
    setDeleting(true)
    setActionError(null)
    try {
      await tenantsApi.delete(id, createIdempotencyKey('tenant_delete'))
      toast.success('Empresa eliminada')
      router.replace(Routes.superadmin.tenants)
    } catch (e) {
      setActionError(toApiError(e))
    } finally {
      setDeleting(false)
    }
  }

  if (loading) return <LoadingSpinner fullScreen label="Cargando empresa..." />

  const displayName = tenant?.trade_name ?? 'Empresa'

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title={displayName} canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {error ? <ApiErrorBanner error={error} /> : null}
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
                <Text style={[styles.name, { color: semantic.text.primary }]}>{displayName}</Text>
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
                <Button variant="danger" size="sm" onPress={() => setConfirmOpen(true)}>
                  Eliminar
                </Button>
              </View>
            </View>

            <DetailSection title="Información fiscal" icon="card-outline">
              <Field label="RUC" value={formatRuc(tenant.ruc)} mono />
              <Field
                label="Entorno SRI"
                value={TENANT_ENVIRONMENT_LABELS[tenant.sri_environment]}
              />
              <Field label="Estado plan" value={TENANT_PLAN_STATUS_LABELS[tenant.plan_status]} />
              <Field label="Plan ID" value={tenant.plan_id} mono />
            </DetailSection>

            <DetailSection title="Contacto" icon="mail-outline">
              <Field label="Email" value={tenant.email} />
              <Field label="Teléfono" value={tenant.phone} />
              <Field label="Dirección" value={tenant.address} />
              <Field label="Creado" value={formatDate(tenant.created_at)} />
              <Field label="Actualizado" value={formatDate(tenant.updated_at)} />
            </DetailSection>
          </>
        ) : null}
      </ScrollView>

      <ConfirmDialog
        visible={confirmOpen}
        title="Eliminar empresa"
        message={`Se desactivará ${displayName} y quedará fuera de la operación.`}
        confirmLabel="Eliminar"
        isLoading={deleting}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={confirmDelete}
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
  avatarText: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  profileCopy: { flex: 1, minWidth: 220, gap: spacing[1] },
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
  field: { flex: 1, minWidth: 220, gap: spacing[1] },
  fieldLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  fieldValue: { fontSize: typography.size.base },
  mono: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.sm },
})
