import React, { useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
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
import { canWrite } from '@/constants/roles'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { sequencesApi } from '../api'
import { EstablishmentCard } from '../components/EstablishmentCard'
import { createEstablishmentSchema } from '../schemas'
import { useEstablishments } from '../hooks/useEstablishments'

export function EstablishmentsScreen() {
  const toast = useToast()
  const { semantic } = useTheme()
  const user = useAuthStore(selectUser)
  const tenantId = user?.tenantId ?? null
  const canManage = canWrite(user?.role ?? null)
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

  const pointsCount = establishments.reduce(
    (total, establishment) => total + establishment.emission_points.length,
    0,
  )
  const testingPoint = establishments
    .find((establishment) => establishment.code === '001')
    ?.emission_points.find((point) => point.code === '099')

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Establecimientos" subtitle="Puntos de emisión SRI" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View
          style={[
            styles.hero,
            { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
          ]}
        >
          <View style={styles.heroCopy}>
            <View style={[styles.heroIcon, { backgroundColor: semantic.accent.subtle }]}>
              <Ionicons name="storefront-outline" size={22} color={semantic.accent.default} />
            </View>
            <View style={styles.heroText}>
              <Text style={[styles.heroTitle, { color: semantic.text.primary }]}>
                Series de emisión SRI
              </Text>
              <Text style={[styles.heroDescription, { color: semantic.text.secondary }]}>
                Define el establecimiento y sus puntos de emisión antes de facturar.
              </Text>
            </View>
          </View>

          <View style={styles.heroMetrics}>
            <Metric label="Establecimientos" value={String(establishments.length)} />
            <Metric label="Puntos de emisión" value={String(pointsCount)} />
            <Metric
              label="Pruebas"
              value={testingPoint ? '001-099' : 'Pendiente'}
              mono={!!testingPoint}
            />
          </View>

          {canManage ? (
            <Button
              variant={newOpen ? 'ghost' : 'primary'}
              size="md"
              onPress={() => setNewOpen((value) => !value)}
            >
              {newOpen ? 'Ocultar formulario' : 'Crear establecimiento'}
            </Button>
          ) : null}
        </View>

        {newOpen && canManage ? (
          <View
            style={[
              styles.createCard,
              { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
            ]}
          >
            <View style={styles.formHeader}>
              <View style={styles.formHeaderCopy}>
                <Text style={[styles.formTitle, { color: semantic.text.primary }]}>
                  Nuevo establecimiento
                </Text>
                <Text style={[styles.formHint, { color: semantic.text.secondary }]}>
                  Usa un código SRI de 3 dígitos. Ejemplo: 001 matriz, 002 sucursal.
                </Text>
              </View>
            </View>

            <View style={styles.formGrid}>
              <View style={styles.codeField}>
                <FormField
                  label="Código SRI"
                  placeholder="002"
                  value={newCode}
                  onChangeText={setNewCode}
                  keyboardType="number-pad"
                  leftIcon="keypad-outline"
                  maxLength={3}
                  required
                />
              </View>
              <View style={styles.labelField}>
                <FormField
                  label="Nombre visible"
                  placeholder="Sucursal Norte"
                  value={newLabel}
                  onChangeText={setNewLabel}
                  leftIcon="bookmark-outline"
                  required
                />
              </View>
            </View>

            {createError ? <ApiErrorBanner error={createError} /> : null}
            <View style={styles.formActions}>
              <Button
                variant="ghost"
                size="md"
                onPress={() => {
                  setNewOpen(false)
                  setNewCode('')
                  setNewLabel('')
                }}
              >
                Cancelar
              </Button>
              <Button
                variant="primary"
                size="md"
                isLoading={creating}
                onPress={() => submitCreate()}
              >
                Guardar establecimiento
              </Button>
            </View>
          </View>
        ) : null}

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
            description="Crea tu primer establecimiento para añadir puntos de emisión y empezar a numerar comprobantes."
            action={
              canManage
                ? {
                    label: 'Crear establecimiento',
                    onPress: () => setNewOpen(true),
                  }
                : undefined
            }
          />
        ) : (
          <View style={styles.establishmentsList}>
            {establishments.map((establishment) => (
              <EstablishmentCard
                key={establishment.code}
                tenantId={tenantId as string}
                establishment={establishment}
                canManage={canManage}
                onChanged={refresh}
              />
            ))}
          </View>
        )}
      </ScrollView>
    </View>
  )
}

function Metric({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  const { semantic } = useTheme()
  return (
    <View style={[styles.metric, { backgroundColor: semantic.bg.secondary }]}>
      <Text style={[styles.metricValue, mono && styles.mono, { color: semantic.text.primary }]}>
        {value}
      </Text>
      <Text style={[styles.metricLabel, { color: semantic.text.secondary }]}>{label}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
  hero: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[4],
    padding: spacing[5],
  },
  heroCopy: { alignItems: 'center', flexDirection: 'row', flex: 1, gap: spacing[3], minWidth: 260 },
  heroIcon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: sizes.icon,
    justifyContent: 'center',
    width: sizes.icon,
  },
  heroText: { flex: 1, gap: spacing[1] },
  heroTitle: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  heroDescription: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
  heroMetrics: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  metric: {
    borderRadius: radius.sm,
    minWidth: 132,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
  },
  metricValue: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  metricLabel: { fontSize: typography.size.xs, marginTop: spacing[1] - 2 },
  mono: { fontFamily: typography.fontFamily.mono },
  createCard: { borderRadius: radius.md, borderWidth: 1, gap: spacing[4], padding: spacing[5] },
  formHeader: { flexDirection: 'row', gap: spacing[3] },
  formHeaderCopy: { flex: 1, gap: spacing[1] },
  formTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  formHint: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
  formGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  codeField: { width: 160 },
  labelField: { flex: 1, minWidth: 240 },
  formActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[2],
    justifyContent: 'flex-end',
  },
  establishmentsList: { gap: spacing[4] },
})
