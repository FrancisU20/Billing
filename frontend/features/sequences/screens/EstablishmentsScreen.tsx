import React, { useState } from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { FormField } from '@/components/ui/FormField'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { Routes } from '@/constants/routes'
import { radius, spacing } from '@/constants/tokens'
import { sequencesApi } from '../api'
import { EstablishmentCard } from '../components/EstablishmentCard'
import { createEstablishmentSchema } from '../schemas'
import { useEstablishments } from '../hooks/useEstablishments'

export function EstablishmentsScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const user = useAuthStore(selectUser)
  const tenantId = user?.tenantId ?? null
  const { establishments, loading, error, refresh } = useEstablishments(tenantId)

  const [newOpen, setNewOpen] = useState(false)
  const [newCode, setNewCode] = useState('')
  const [newLabel, setNewLabel] = useState('')

  const {
    submitting: creating,
    error: createError,
    submit: submitCreate,
  } = useFormSubmit(async () => {
    if (!tenantId) return
    await sequencesApi.create(
      tenantId,
      createEstablishmentSchema.parse({ code: newCode.trim(), label: newLabel.trim() }),
      createIdempotencyKey('establishment_create'),
    )
    toast.success('Establecimiento creado')
    setNewOpen(false)
    setNewCode('')
    setNewLabel('')
    await refresh()
  })

  if (loading) return <LoadingSpinner fullScreen label="Cargando establecimientos..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Establecimientos" subtitle="Puntos de emisión SRI" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {error ? (
          <EmptyState
            icon="alert-circle-outline"
            title="No se pudieron cargar los establecimientos"
            description={error.message}
            action={{ label: 'Reintentar', onPress: refresh }}
          />
        ) : establishments.length === 0 && !newOpen ? (
          <EmptyState
            icon="storefront-outline"
            title="Sin establecimientos"
            description="Sube tu certificado digital desde el dashboard para que se cree automáticamente tu punto de pruebas, o crea uno manualmente."
            action={{
              label: 'Ir al dashboard',
              onPress: () => router.push(Routes.tenant.dashboard as Href),
            }}
          />
        ) : (
          establishments.map((establishment) => (
            <EstablishmentCard
              key={establishment.code}
              tenantId={tenantId as string}
              establishment={establishment}
              onChanged={refresh}
            />
          ))
        )}

        <View
          style={[
            styles.newCard,
            { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
          ]}
        >
          {newOpen ? (
            <>
              <FormField
                label="Código"
                placeholder="002"
                value={newCode}
                onChangeText={setNewCode}
                keyboardType="number-pad"
                leftIcon="pricetag-outline"
              />
              <FormField
                label="Etiqueta"
                placeholder="Sucursal Norte"
                value={newLabel}
                onChangeText={setNewLabel}
                leftIcon="bookmark-outline"
              />
              {createError ? <ApiErrorBanner error={createError} /> : null}
              <View style={styles.newCardActions}>
                <Button variant="ghost" size="md" onPress={() => setNewOpen(false)}>
                  Cancelar
                </Button>
                <Button
                  variant="primary"
                  size="md"
                  isLoading={creating}
                  onPress={() => submitCreate()}
                >
                  Crear establecimiento
                </Button>
              </View>
            </>
          ) : (
            <Button variant="outline" size="md" fullWidth onPress={() => setNewOpen(true)}>
              Nuevo establecimiento
            </Button>
          )}
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
  newCard: { borderRadius: radius.md, borderWidth: 1, gap: spacing[3], padding: spacing[4] },
  newCardActions: { flexDirection: 'row', gap: spacing[2], justifyContent: 'flex-end' },
})
