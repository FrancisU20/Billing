import React, { useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { DetailField, DetailSection } from '@/components/ui/DetailSection'
import { DetailHeader } from '@/components/ui/DetailHeader'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { formatDateTime, initials } from '@/lib/utils/format'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { canWrite } from '@/constants/roles'
import { radius, spacing, typography } from '@/constants/tokens'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { clientsApi } from '../api'
import { ClientStatusBadge } from '../components/ClientStatusBadge'
import { CLIENT_IDENTIFICATION_LABELS, CLIENT_PERSON_LABELS } from '../constants'
import { useClient } from '../hooks/useClient'

export function ClientDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const role = useAuthStore((state) => selectUser(state)?.role ?? null)
  const canManage = canWrite(role)
  const { client, loading, error, refresh } = useClient(id ?? null)
  const [confirmOpen, setConfirmOpen] = useState(false)

  useRefreshOnFocus(refresh)

  const {
    submitting: deleting,
    error: actionError,
    submit: confirmDelete,
  } = useFormSubmit(async () => {
    if (!id) return
    await clientsApi.delete(id, createIdempotencyKey('client_delete'))
    toast.success('Cliente eliminado')
    router.replace(Routes.tenant.clients as Href)
  })

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
                <DetailHeader
                  title={displayName}
                  subtitle={client.legal_name}
                  initials={initials(displayName)}
                  badges={
                    <>
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
                    </>
                  }
                  actions={
                    canManage ? (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          onPress={() => router.push(Routes.tenant.clientEdit(client.id) as Href)}
                        >
                          Editar
                        </Button>
                        {client.status === 'active' ? (
                          <Button variant="danger" size="sm" onPress={() => setConfirmOpen(true)}>
                            Eliminar
                          </Button>
                        ) : null}
                      </>
                    ) : null
                  }
                />

                <DetailSection title="Información fiscal" icon="card-outline">
                  <DetailField
                    label={CLIENT_IDENTIFICATION_LABELS[client.identification_type]}
                    value={client.identification}
                    mono
                  />
                  <DetailField
                    label="Tipo de persona"
                    value={CLIENT_PERSON_LABELS[client.person_type]}
                  />
                  <DetailField label="Creado" value={formatDateTime(client.created_at)} />
                  <DetailField label="Actualizado" value={formatDateTime(client.updated_at)} />
                </DetailSection>

                <DetailSection title="Contacto" icon="mail-outline">
                  <DetailField label="Email" value={client.emails[0] ?? 'Sin email'} />
                  <DetailField label="Teléfono" value={client.phones[0] ?? 'Sin teléfono'} />
                  <DetailField
                    label="Dirección"
                    value={client.addresses[0]?.line ?? 'Sin dirección'}
                  />
                  <DetailField label="Ciudad" value={client.addresses[0]?.city || 'Sin ciudad'} />
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

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
  smallBadge: { borderRadius: radius.full, paddingHorizontal: spacing[2], paddingVertical: 2 },
  smallBadgeText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
})
