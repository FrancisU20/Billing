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
import { formatDate, initials } from '@/lib/utils/format'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { clientsApi } from '../api'
import { ClientStatusBadge } from '../components/ClientStatusBadge'
import { CLIENT_IDENTIFICATION_LABELS, CLIENT_PERSON_LABELS } from '../constants'
import { useClient } from '../hooks/useClient'

export function ClientDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { client, loading, error, refresh } = useClient(id ?? null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState<ApiError | null>(null)

  async function confirmDelete() {
    if (!id) return
    setDeleting(true)
    setActionError(null)
    try {
      await clientsApi.delete(id, createIdempotencyKey('client_delete'))
      toast.success('Cliente eliminado')
      router.replace(Routes.tenant.clients as Href)
    } catch (e) {
      setActionError(toApiError(e))
    } finally {
      setDeleting(false)
    }
  }

  if (loading) return <LoadingSpinner fullScreen label="Cargando cliente..." />

  const displayName = client ? client.trade_name || client.legal_name : 'Cliente'

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title={displayName} canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {error ? (
          <EmptyState
            icon="alert-circle-outline"
            title="No se pudo cargar el cliente"
            description={error.message}
            action={{ label: 'Reintentar', onPress: refresh }}
          />
        ) : (
          <>
            {actionError ? <ApiErrorBanner error={actionError} /> : null}

            {client ? (
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
                      {client.legal_name}
                    </Text>
                    <View style={styles.badgeRow}>
                      <ClientStatusBadge status={client.status} />
                      {client.special_taxpayer ? (
                        <View
                          style={[
                            styles.smallBadge,
                            { backgroundColor: semantic.accent.altSubtle },
                          ]}
                        >
                          <Text style={[styles.smallBadgeText, { color: semantic.accent.alt }]}>
                            Especial
                          </Text>
                        </View>
                      ) : null}
                    </View>
                  </View>
                  <View style={styles.profileActions}>
                    <Button
                      variant="outline"
                      size="sm"
                      onPress={() => router.push(Routes.tenant.clientEdit(client.id) as Href)}
                    >
                      Editar
                    </Button>
                    <Button variant="danger" size="sm" onPress={() => setConfirmOpen(true)}>
                      Eliminar
                    </Button>
                  </View>
                </View>

                <DetailSection title="Información fiscal" icon="card-outline">
                  <Field
                    label={CLIENT_IDENTIFICATION_LABELS[client.identification_type]}
                    value={client.identification}
                    mono
                  />
                  <Field label="Tipo de persona" value={CLIENT_PERSON_LABELS[client.person_type]} />
                  <Field label="Creado" value={formatDate(client.created_at)} />
                  <Field label="Actualizado" value={formatDate(client.updated_at)} />
                </DetailSection>

                <DetailSection title="Contacto" icon="mail-outline">
                  <Field label="Email" value={client.emails[0] ?? 'Sin email'} />
                  <Field label="Teléfono" value={client.phones[0] ?? 'Sin teléfono'} />
                  <Field label="Dirección" value={client.addresses[0]?.line ?? 'Sin dirección'} />
                  <Field label="Ciudad" value={client.addresses[0]?.city || 'Sin ciudad'} />
                </DetailSection>
              </>
            ) : null}
          </>
        )}
      </ScrollView>

      <ConfirmDialog
        visible={confirmOpen}
        title="Eliminar cliente"
        message={`Se desactivará ${displayName} y su identificación podrá reutilizarse.`}
        confirmLabel="Eliminar"
        isLoading={deleting}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={confirmDelete}
      />
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
