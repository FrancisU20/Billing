import React, { useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { ListItemAction } from '@/components/ui/ListItemPrimitives'
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
          <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
            Establecimiento {establishment.code}
          </Text>
        </View>
        {canManage ? (
          <Button variant="outline" size="sm" onPress={() => setAddOpen((v) => !v)}>
            {addOpen ? 'Cancelar' : 'Punto de emisión'}
          </Button>
        ) : null}
      </View>

      <View style={styles.pointsList}>
        {establishment.emission_points.map((point) => (
          <View
            key={point.code}
            style={[styles.pointRow, { borderColor: semantic.border.default }]}
          >
            {editingCode === point.code ? (
              <View style={styles.editRow}>
                <View style={styles.editLabelInput}>
                  <Input value={editLabel} onChangeText={setEditLabel} placeholder="Etiqueta" />
                </View>
                <View style={styles.editInitialInput}>
                  <Input
                    value={editInitial}
                    onChangeText={setEditInitial}
                    placeholder="Secuencial"
                    keyboardType="number-pad"
                  />
                </View>
                <Button
                  variant="primary"
                  size="sm"
                  isLoading={editingPoint}
                  onPress={() => submitEditPoint()}
                >
                  Guardar
                </Button>
                <Button variant="ghost" size="sm" onPress={() => setEditingCode(null)}>
                  Cancelar
                </Button>
              </View>
            ) : (
              <>
                <View style={styles.pointCopy}>
                  <Text style={[styles.pointLabel, { color: semantic.text.primary }]}>
                    {point.label}
                  </Text>
                  <Text style={[styles.pointMeta, { color: semantic.text.secondary }]}>
                    Punto {point.code} · inicia en {point.initial_sequential}
                  </Text>
                </View>
                {canManage ? (
                  <ListItemAction
                    icon="create-outline"
                    label={`Editar punto ${point.code}`}
                    onPress={() => {
                      setEditingCode(point.code)
                      setEditLabel(point.label)
                      setEditInitial(String(point.initial_sequential))
                    }}
                  />
                ) : null}
              </>
            )}
          </View>
        ))}
      </View>

      {editError ? <ApiErrorBanner error={editError} /> : null}

      {addOpen && canManage ? (
        <View style={styles.addForm}>
          <FormField
            label="Código"
            placeholder="001"
            value={pointCode}
            onChangeText={setPointCode}
            keyboardType="number-pad"
            leftIcon="pricetag-outline"
          />
          <FormField
            label="Etiqueta"
            placeholder="Caja 1"
            value={pointLabel}
            onChangeText={setPointLabel}
            leftIcon="bookmark-outline"
          />
          <FormField
            label="Secuencial inicial"
            placeholder="1"
            value={pointInitial}
            onChangeText={setPointInitial}
            keyboardType="number-pad"
            leftIcon="trending-up-outline"
            hint="Usa un valor mayor a 1 si ya facturabas con otro sistema y quieres continuar la numeración."
          />
          {addError ? <ApiErrorBanner error={addError} /> : null}
          <Button
            variant="primary"
            size="md"
            isLoading={addingPoint}
            onPress={() => submitAddPoint()}
          >
            Agregar punto de emisión
          </Button>
        </View>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  card: { borderRadius: radius.md, borderWidth: 1, gap: spacing[4], padding: spacing[4] },
  header: { alignItems: 'center', flexDirection: 'row', gap: spacing[3] },
  icon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: sizes.icon,
    justifyContent: 'center',
    width: sizes.icon,
  },
  headerCopy: { flex: 1, gap: spacing[1] - 2 },
  title: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  subtitle: { fontSize: typography.size.xs },
  pointsList: { gap: spacing[2] },
  pointRow: {
    alignItems: 'center',
    borderRadius: radius.sm,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[2],
    padding: spacing[3],
  },
  pointCopy: { flex: 1, gap: spacing[1] - 2 },
  pointLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  pointMeta: { fontSize: typography.size.xs },
  editRow: {
    alignItems: 'center',
    flex: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[2],
  },
  editLabelInput: { flex: 1, minWidth: 140 },
  editInitialInput: { width: 120 },
  addForm: { gap: spacing[3] },
})
