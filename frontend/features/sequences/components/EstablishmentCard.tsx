import React, { useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { sequencesApi } from '../api'
import { addEmissionPointSchema, editEmissionPointSchema } from '../schemas'
import type { Establishment } from '../types'

interface EstablishmentCardProps {
  tenantId: string
  establishment: Establishment
  canManage: boolean
  onChanged: () => Promise<void> | void
}

export function EstablishmentCard({
  tenantId,
  establishment,
  canManage,
  onChanged,
}: EstablishmentCardProps) {
  const { semantic } = useTheme()
  const [addOpen, setAddOpen] = useState(false)
  const [pointCode, setPointCode] = useState('')
  const [pointLabel, setPointLabel] = useState('')
  const [pointInitial, setPointInitial] = useState('1')
  const [editingCode, setEditingCode] = useState<string | null>(null)
  const [editLabel, setEditLabel] = useState('')
  const [editInitial, setEditInitial] = useState('')

  const {
    submitting: addingPoint,
    error: addError,
    submit: submitAddPoint,
  } = useFormSubmit(async () => {
    await sequencesApi.addEmissionPoint(
      tenantId,
      establishment.code,
      addEmissionPointSchema.parse({
        code: pointCode.trim(),
        label: pointLabel.trim(),
        initial_sequential: Number(pointInitial) || 1,
      }),
      createIdempotencyKey('emission_point_add'),
    )
    setAddOpen(false)
    setPointCode('')
    setPointLabel('')
    setPointInitial('1')
    await onChanged()
  })

  const {
    submitting: editingPoint,
    error: editError,
    submit: submitEditPoint,
  } = useFormSubmit(async () => {
    if (!editingCode) return
    await sequencesApi.editEmissionPoint(
      tenantId,
      establishment.code,
      editingCode,
      editEmissionPointSchema.parse({
        label: editLabel.trim() || undefined,
        initial_sequential: editInitial.trim() ? Number(editInitial) : undefined,
      }),
      createIdempotencyKey('emission_point_edit'),
    )
    setEditingCode(null)
    await onChanged()
  })

  function closeAddForm() {
    setAddOpen(false)
    setPointCode('')
    setPointLabel('')
    setPointInitial('1')
  }

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.header}>
        <View style={[styles.icon, { backgroundColor: semantic.accent.subtle }]}>
          <Ionicons name="storefront-outline" size={18} color={semantic.accent.default} />
        </View>
        <View style={styles.headerCopy}>
          <Text style={[styles.title, { color: semantic.text.primary }]}>
            {establishment.label}
          </Text>
          <View style={styles.headerMeta}>
            <Text
              style={[
                styles.codePill,
                styles.mono,
                { color: semantic.accent.default, backgroundColor: semantic.accent.subtle },
              ]}
            >
              Estab. {establishment.code}
            </Text>
            <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
              {establishment.emission_points.length} punto
              {establishment.emission_points.length === 1 ? '' : 's'} de emisión
            </Text>
          </View>
        </View>
        {canManage ? (
          <Button
            variant={addOpen ? 'ghost' : 'outline'}
            size="sm"
            onPress={() => setAddOpen((v) => !v)}
          >
            {addOpen ? 'Ocultar' : 'Agregar punto'}
          </Button>
        ) : null}
      </View>

      {addOpen && canManage ? (
        <View
          style={[
            styles.addForm,
            { backgroundColor: semantic.bg.secondary, borderColor: semantic.border.default },
          ]}
        >
          <View style={styles.formHeader}>
            <Text style={[styles.formTitle, { color: semantic.text.primary }]}>
              Nuevo punto de emisión
            </Text>
            <Text style={[styles.formHint, { color: semantic.text.secondary }]}>
              Creará la serie {establishment.code}-XXX. El punto 099 está reservado para pruebas.
            </Text>
          </View>

          <View style={styles.formGrid}>
            <View style={styles.codeInput}>
              <FormField
                label="Punto SRI"
                placeholder="001"
                value={pointCode}
                onChangeText={setPointCode}
                keyboardType="number-pad"
                leftIcon="keypad-outline"
                maxLength={3}
                required
              />
            </View>
            <View style={styles.labelInput}>
              <FormField
                label="Nombre visible"
                placeholder="Caja principal"
                value={pointLabel}
                onChangeText={setPointLabel}
                leftIcon="bookmark-outline"
                required
              />
            </View>
            <View style={styles.initialInput}>
              <FormField
                label="Primer secuencial"
                placeholder="1"
                value={pointInitial}
                onChangeText={setPointInitial}
                keyboardType="number-pad"
                leftIcon="trending-up-outline"
                hint="Usa el siguiente número si vienes de otro sistema."
                required
              />
            </View>
          </View>

          {addError ? <ApiErrorBanner error={addError} /> : null}
          <View style={styles.formActions}>
            <Button variant="ghost" size="md" onPress={closeAddForm}>
              Cancelar
            </Button>
            <Button
              variant="primary"
              size="md"
              isLoading={addingPoint}
              onPress={() => submitAddPoint()}
            >
              Guardar punto
            </Button>
          </View>
        </View>
      ) : null}

      <View style={styles.pointsList}>
        {establishment.emission_points.length > 0 ? (
          establishment.emission_points.map((point) => (
            <View
              key={point.code}
              style={[
                styles.pointRow,
                { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
              ]}
            >
              {editingCode === point.code ? (
                <View style={styles.editPanel}>
                  <View style={styles.formGrid}>
                    <View style={styles.labelInput}>
                      <FormField
                        label="Nombre visible"
                        value={editLabel}
                        onChangeText={setEditLabel}
                        placeholder="Caja principal"
                        leftIcon="bookmark-outline"
                      />
                    </View>
                    <View style={styles.initialInput}>
                      <FormField
                        label="Primer secuencial"
                        value={editInitial}
                        onChangeText={setEditInitial}
                        placeholder="1"
                        keyboardType="number-pad"
                        leftIcon="trending-up-outline"
                      />
                    </View>
                  </View>
                  {editError ? <ApiErrorBanner error={editError} /> : null}
                  <View style={styles.formActions}>
                    <Button variant="ghost" size="sm" onPress={() => setEditingCode(null)}>
                      Cancelar
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      isLoading={editingPoint}
                      onPress={() => submitEditPoint()}
                    >
                      Guardar cambios
                    </Button>
                  </View>
                </View>
              ) : (
                <>
                  <View style={[styles.seriesBadge, { backgroundColor: semantic.accent.subtle }]}>
                    <Text
                      style={[styles.seriesText, styles.mono, { color: semantic.accent.default }]}
                    >
                      {establishment.code}-{point.code}
                    </Text>
                  </View>

                  <View style={styles.pointCopy}>
                    <View style={styles.pointTitleRow}>
                      <Text style={[styles.pointLabel, { color: semantic.text.primary }]}>
                        {point.label}
                      </Text>
                      {point.code === '099' ? (
                        <Text
                          style={[
                            styles.testingPill,
                            { color: semantic.status.warning, backgroundColor: semantic.bg.muted },
                          ]}
                        >
                          Pruebas
                        </Text>
                      ) : null}
                    </View>
                    <Text style={[styles.pointMeta, { color: semantic.text.secondary }]}>
                      Primer secuencial {point.initial_sequential.toLocaleString('es-EC')} · Primer
                      comprobante {establishment.code}-{point.code}-
                      {formatSriSequential(point.initial_sequential)}
                    </Text>
                  </View>

                  {canManage ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onPress={() => {
                        setEditingCode(point.code)
                        setEditLabel(point.label)
                        setEditInitial(String(point.initial_sequential))
                      }}
                    >
                      Editar
                    </Button>
                  ) : null}
                </>
              )}
            </View>
          ))
        ) : (
          <View
            style={[
              styles.emptyPoints,
              { backgroundColor: semantic.bg.secondary, borderColor: semantic.border.default },
            ]}
          >
            <Text style={[styles.emptyTitle, { color: semantic.text.primary }]}>
              Sin puntos de emisión
            </Text>
            <Text style={[styles.emptyCopy, { color: semantic.text.secondary }]}>
              Agrega al menos un punto para emitir facturas desde este establecimiento.
            </Text>
            {canManage ? (
              <Button variant="outline" size="sm" onPress={() => setAddOpen(true)}>
                Agregar punto
              </Button>
            ) : null}
          </View>
        )}
      </View>
    </View>
  )
}

function formatSriSequential(value: number) {
  return String(value).padStart(9, '0')
}

const styles = StyleSheet.create({
  card: { borderRadius: radius.md, borderWidth: 1, gap: spacing[4], padding: spacing[4] },
  header: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  icon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: sizes.icon,
    justifyContent: 'center',
    width: sizes.icon,
  },
  headerCopy: { flex: 1, gap: spacing[1] - 2 },
  title: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  headerMeta: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  codePill: {
    borderRadius: radius.sm,
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1] - 2,
  },
  subtitle: { fontSize: typography.size.xs },
  pointsList: { gap: spacing[2] },
  pointRow: {
    alignItems: 'center',
    borderRadius: radius.sm,
    borderWidth: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
    padding: spacing[3],
  },
  seriesBadge: {
    alignItems: 'center',
    borderRadius: radius.sm,
    justifyContent: 'center',
    minHeight: 44,
    minWidth: 88,
    paddingHorizontal: spacing[3],
  },
  seriesText: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  pointCopy: { flex: 1, gap: spacing[1] - 2 },
  pointTitleRow: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  pointLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  testingPill: {
    borderRadius: radius.full,
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1] - 2,
  },
  pointMeta: { fontSize: typography.size.xs },
  editPanel: { flex: 1, gap: spacing[3], minWidth: 260 },
  addForm: { borderRadius: radius.md, borderWidth: 1, gap: spacing[4], padding: spacing[4] },
  formHeader: { gap: spacing[1] },
  formTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  formHint: {
    fontSize: typography.size.xs,
    lineHeight: typography.size.xs * typography.lineHeight.normal,
  },
  formGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  codeInput: { width: 140 },
  labelInput: { flex: 1, minWidth: 220 },
  initialInput: { width: 190 },
  formActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[2],
    justifyContent: 'flex-end',
  },
  emptyPoints: {
    alignItems: 'flex-start',
    borderRadius: radius.sm,
    borderWidth: 1,
    gap: spacing[2],
    padding: spacing[4],
  },
  emptyTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  emptyCopy: {
    fontSize: typography.size.xs,
    lineHeight: typography.size.xs * typography.lineHeight.normal,
  },
  mono: { fontFamily: typography.fontFamily.mono },
})
