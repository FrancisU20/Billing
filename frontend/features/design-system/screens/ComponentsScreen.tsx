import React, { useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ApiError } from '@/lib/api/errors'
import { useTheme } from '@/lib/theme-context'
import { Logo } from '@/components/branding/Logo'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { Divider } from '@/components/ui/Divider'
import { DetailField, DetailSection } from '@/components/ui/DetailSection'
import { StatMetric } from '@/components/ui/StatMetric'
import { ListItemAction, ListItemMeta } from '@/components/ui/ListItemPrimitives'
import { colors, radius, spacing, typography } from '@/constants/tokens'

const buttonVariants = ['primary', 'secondary', 'outline', 'ghost', 'warning', 'danger'] as const
const badgeVariants = ['success', 'warning', 'error', 'neutral', 'primary', 'accent'] as const
const semanticSwatches = [
  { label: 'Accent', key: 'accent.default' },
  { label: 'Alt', key: 'accent.alt' },
  { label: 'Tertiary', key: 'accent.tertiary' },
  { label: 'Success', key: 'status.success' },
  { label: 'Warning', key: 'status.warning' },
  { label: 'Error', key: 'status.error' },
] as const
const rawSwatches = [
  { label: 'Primary', color: colors.primary[500] },
  { label: 'Cyan', color: colors.cyan[500] },
  { label: 'Teal', color: colors.teal[500] },
  { label: 'Neutral', color: colors.neutral[700] },
  { label: 'Success', color: colors.success[500] },
  { label: 'Warning', color: colors.warning[500] },
  { label: 'Error', color: colors.error[500] },
] as const

type ThemeMode = 'base' | 'form' | 'states'

export function ComponentsScreen() {
  const { semantic, colorScheme } = useTheme()
  const [segment, setSegment] = useState<ThemeMode>('base')
  const error = new ApiError('NETWORK_ERROR', 'No se pudo conectar con el API.', 0)

  const semanticColor = (key: (typeof semanticSwatches)[number]['key']) => {
    const [group, name] = key.split('.') as ['accent' | 'status', string]
    return semantic[group][name as never] as string
  }

  return (
    <View style={[styles.page, { backgroundColor: semantic.bg.page }]}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <View style={styles.titleRow}>
            <Logo size={52} />
            <View style={styles.titleCopy}>
              <Text style={[styles.eyebrow, { color: semantic.accent.default }]}>
                Design system
              </Text>
              <Text style={[styles.title, { color: semantic.text.primary }]}>Componentes</Text>
              <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
                Tema activo: {colorScheme}
              </Text>
            </View>
          </View>
          <SegmentedControl
            value={segment}
            onChange={setSegment}
            options={[
              { value: 'base', label: 'Base' },
              { value: 'form', label: 'Forms' },
              { value: 'states', label: 'Estados' },
            ]}
          />
        </View>

        <Section title="Identidad">
          <View style={styles.logoRow}>
            <Logo size={40} />
            <Logo size={64} />
            <Logo size={96} />
          </View>
          <Card variant="muted">
            <View style={styles.inlineLoader}>
              <LoadingSpinner size="small" compact />
              <LoadingSpinner label="Cargando planes..." />
            </View>
          </Card>
        </Section>

        <Section title="Colores">
          <Text style={[styles.sectionNote, { color: semantic.text.secondary }]}>Semánticos</Text>
          <View style={styles.swatchGrid}>
            {semanticSwatches.map((swatch) => (
              <Swatch key={swatch.key} label={swatch.label} color={semanticColor(swatch.key)} />
            ))}
          </View>
          <Text style={[styles.sectionNote, { color: semantic.text.secondary }]}>Paleta</Text>
          <View style={styles.swatchGrid}>
            {rawSwatches.map((swatch) => (
              <Swatch key={swatch.label} label={swatch.label} color={swatch.color} />
            ))}
          </View>
        </Section>

        <Section title="Botones">
          <View style={styles.componentRow}>
            {buttonVariants.map((variant) => (
              <Button key={variant} variant={variant} size="md" onPress={() => undefined}>
                {variant}
              </Button>
            ))}
            <Button variant="primary" isLoading onPress={() => undefined}>
              Guardando
            </Button>
            <Button variant="secondary" isDisabled onPress={() => undefined}>
              Deshabilitado
            </Button>
          </View>
        </Section>

        <Section title="Inputs">
          <View style={styles.formGrid}>
            <FormField
              label="RUC"
              required
              leftIcon="business-outline"
              placeholder="1790012345001"
              value="1790012345001"
            />
            <FormField
              label="Correo"
              leftIcon="mail-outline"
              placeholder="admin@empresa.com"
              value="admin@empresa.com"
              hint="Se usa para notificaciones del tenant."
            />
            <FormField
              label="Clave"
              leftIcon="lock-closed-outline"
              value="Temporal123"
              secureTextEntry
            />
            <FormField
              label="Ambiente SRI"
              value="producción"
              error="Selecciona un ambiente válido."
            />
            <Input leftIcon="search-outline" placeholder="Buscar componentes" />
            <Input value="Campo deshabilitado" isDisabled />
          </View>
        </Section>

        <Section title="Badges y métricas">
          <View style={styles.componentRow}>
            {badgeVariants.map((variant) => (
              <Badge key={variant} label={variant} variant={variant} />
            ))}
          </View>
          <View style={styles.metricsRow}>
            <StatMetric label="Planes" value={12} icon="layers-outline" />
            <StatMetric label="Clientes" value={48} icon="people-outline" />
            <StatMetric label="Activos" value={32} icon="checkmark-circle-outline" />
          </View>
        </Section>

        <Section title="Cards y detalle">
          <View style={styles.cardGrid}>
            <Card>
              <View style={styles.cardStack}>
                <Badge label="default" variant="primary" size="sm" />
                <Text style={[styles.cardTitle, { color: semantic.text.primary }]}>Card base</Text>
                <Text style={[styles.body, { color: semantic.text.secondary }]}>
                  Superficie con borde para formularios, resúmenes y bloques de lectura.
                </Text>
              </View>
            </Card>
            <Card variant="elevated" elevated>
              <View style={styles.cardStack}>
                <Badge label="elevated" variant="accent" size="sm" />
                <Text style={[styles.cardTitle, { color: semantic.text.primary }]}>
                  Card elevada
                </Text>
                <View style={styles.metaRow}>
                  <ListItemMeta icon="calendar-outline" text="2026-06-13" />
                  <ListItemMeta icon="terminal-outline" text="CLB-001" mono />
                </View>
                <View style={styles.actionRow}>
                  <ListItemAction icon="eye-outline" label="Ver" onPress={() => undefined} />
                  <ListItemAction
                    icon="trash-outline"
                    label="Eliminar"
                    danger
                    onPress={() => undefined}
                  />
                </View>
              </View>
            </Card>
          </View>
          <DetailSection title="Tenant" icon="business-outline">
            <DetailField label="Empresa" value="CodeLabs Ecuador" />
            <DetailField label="RUC" value="1790012345001" mono />
            <DetailField label="Plan" value="Profesional" />
          </DetailSection>
        </Section>

        <Section title="Estados">
          <ApiErrorBanner error={error} />
          <Card variant="muted" padded={false}>
            <EmptyState
              icon="file-tray-outline"
              title="Sin resultados"
              description="No hay elementos que coincidan con los filtros actuales."
              action={{ label: 'Reintentar', onPress: () => undefined }}
            />
          </Card>
        </Section>

        <Section title="Escalas">
          <View style={styles.scaleRow}>
            {[spacing[1], spacing[2], spacing[3], spacing[4], spacing[6], spacing[8]].map(
              (value) => (
                <View key={value} style={styles.scaleItem}>
                  <View
                    style={[
                      styles.scaleBlock,
                      { width: value, backgroundColor: semantic.accent.default },
                    ]}
                  />
                  <Text style={[styles.scaleLabel, { color: semantic.text.secondary }]}>
                    {value}px
                  </Text>
                </View>
              ),
            )}
          </View>
          <Divider />
          <View style={styles.radiusRow}>
            {([radius.xs, radius.sm, radius.md, radius.lg, radius.xl] as const).map((value) => (
              <View
                key={value}
                style={[
                  styles.radiusBox,
                  {
                    borderRadius: value,
                    borderColor: semantic.border.default,
                    backgroundColor: semantic.bg.card,
                  },
                ]}
              >
                <Text style={[styles.scaleLabel, { color: semantic.text.secondary }]}>{value}</Text>
              </View>
            ))}
          </View>
        </Section>
      </ScrollView>
    </View>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Ionicons name="grid-outline" size={16} color={semantic.accent.default} />
        <Text style={[styles.sectionTitle, { color: semantic.text.primary }]}>{title}</Text>
      </View>
      {children}
    </View>
  )
}

function Swatch({ label, color }: { label: string; color: string }) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.swatch,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={[styles.swatchColor, { backgroundColor: color }]} />
      <View style={styles.swatchCopy}>
        <Text style={[styles.swatchLabel, { color: semantic.text.primary }]}>{label}</Text>
        <Text style={[styles.swatchValue, { color: semantic.text.secondary }]}>{color}</Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1 },
  content: {
    alignSelf: 'center',
    gap: spacing[6],
    maxWidth: 1180,
    padding: spacing[5],
    paddingBottom: spacing[12],
    width: '100%',
  },
  header: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[5],
    justifyContent: 'space-between',
  },
  titleRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[4] },
  titleCopy: { gap: spacing[1] },
  eyebrow: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
    textTransform: 'uppercase',
  },
  title: { fontSize: typography.size['3xl'], fontWeight: typography.weight.bold },
  subtitle: { fontSize: typography.size.sm },
  section: { gap: spacing[4] },
  sectionHeader: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  sectionTitle: { fontSize: typography.size.xl, fontWeight: typography.weight.bold },
  sectionNote: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  logoRow: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  inlineLoader: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  swatchGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  swatch: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    minWidth: 190,
    padding: spacing[3],
  },
  swatchColor: { borderRadius: radius.md, height: 34, width: 34 },
  swatchCopy: { gap: spacing[1], minWidth: 0 },
  swatchLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  swatchValue: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.xs },
  componentRow: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  formGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  metricsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  cardGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  cardStack: { gap: spacing[3], minWidth: 260 },
  cardTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  body: { fontSize: typography.size.sm, lineHeight: typography.size.sm * 1.6 },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  actionRow: { flexDirection: 'row', gap: spacing[2] },
  scaleRow: { alignItems: 'flex-end', flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  scaleItem: { alignItems: 'center', gap: spacing[2] },
  scaleBlock: { borderRadius: radius.xs, height: 36 },
  scaleLabel: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.xs },
  radiusRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  radiusBox: {
    alignItems: 'center',
    borderWidth: 1,
    height: 52,
    justifyContent: 'center',
    width: 72,
  },
})
