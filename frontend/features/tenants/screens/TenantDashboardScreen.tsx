import React from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing, radius, shadow } from '@/constants/tokens'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { Card } from '@/components/ui/Card'
import { useAuthStore, selectUser } from '@/features/auth/store'
import { RoleLabel } from '@/constants/roles'
import { useTenant } from '@/features/tenants/hooks/useTenant'

type MetricTone = 'primary' | 'secondary' | 'error'

const dashboardMetrics = [
  {
    icon: 'document-text-outline',
    label: 'Documentos emitidos',
    value: '—',
    detail: 'Sin actividad registrada',
    tone: 'primary',
  },
  {
    icon: 'pulse-outline',
    label: 'Autorizaciones',
    value: '—',
    detail: 'Sin datos del SRI',
    tone: 'secondary',
  },
  {
    icon: 'alert-circle-outline',
    label: 'Con error',
    value: '—',
    detail: 'Sin emisiones registradas',
    tone: 'error',
  },
] as const

const modulePreview = [
  { icon: 'receipt-outline', title: 'Facturas', subtitle: 'Emisión SRI' },
  {
    icon: 'return-down-back-outline',
    title: 'Notas de crédito',
    subtitle: 'Ajustes y anulaciones',
  },
  { icon: 'shield-checkmark-outline', title: 'Retenciones', subtitle: 'Comprobantes fiscales' },
] as const

export function TenantDashboardScreen() {
  const user = useAuthStore(selectUser)
  const { semantic } = useTheme()
  const roleLabel = user?.role ? RoleLabel[user.role] : 'Sin rol'
  const { tenant, loading: tenantLoading } = useTenant(user?.tenantId ?? null)

  const companyName = tenantLoading ? '...' : (tenant?.trade_name ?? 'Mi Empresa')

  const sriBadge = tenant?.sri_environment === 'production' ? 'Producción' : 'Pruebas'

  return (
    <View style={[staticStyles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title={companyName} subtitle="Dashboard" />

      <ScrollView contentContainerStyle={staticStyles.scroll} showsVerticalScrollIndicator={false}>
        <View
          style={[
            staticStyles.hero,
            { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
          ]}
        >
          <View style={[staticStyles.heroAccent, { backgroundColor: semantic.accent.default }]} />
          <View style={staticStyles.heroTop}>
            <View style={[staticStyles.avatar, { backgroundColor: semantic.accent.default }]}>
              <Text style={[staticStyles.avatarText, { color: semantic.text.onDark }]}>
                {user?.email?.charAt(0).toUpperCase() ?? '?'}
              </Text>
            </View>
            <View style={staticStyles.identity}>
              <Text style={[staticStyles.kicker, { color: semantic.accent.default }]}>
                Cuenta activa
              </Text>
              <Text
                style={[staticStyles.email, { color: semantic.text.primary }]}
                numberOfLines={1}
              >
                {user?.email ?? ''}
              </Text>
            </View>
            <View
              style={[
                staticStyles.rolePill,
                { backgroundColor: semantic.accent.subtle, borderColor: semantic.border.default },
              ]}
            >
              <Text
                style={[staticStyles.roleText, { color: semantic.accent.default }]}
                numberOfLines={1}
              >
                {roleLabel}
              </Text>
            </View>
          </View>

          <View style={staticStyles.heroCopy}>
            <Text style={[staticStyles.heroTitle, { color: semantic.text.primary }]}>
              Centro de facturación
            </Text>
            <Text style={[staticStyles.heroSubtitle, { color: semantic.text.secondary }]}>
              Resumen operativo de documentos, autorizaciones y módulos disponibles.
            </Text>
          </View>

          <View style={[staticStyles.heroFooter, { borderTopColor: semantic.border.default }]}>
            <HeroSignal label="Estado" value="En línea" />
            <HeroSignal label="Periodo" value="Actual" />
            <HeroSignal label="Ambiente" value={sriBadge} />
          </View>
        </View>

        <SectionHeader title="Resumen operativo" caption="Actividad del periodo" />
        <View style={staticStyles.metricGrid}>
          {dashboardMetrics.map((metric) => (
            <MetricCard
              key={metric.label}
              icon={metric.icon}
              label={metric.label}
              value={metric.value}
              detail={metric.detail}
              tone={metric.tone}
            />
          ))}
        </View>

        <Card variant="elevated" elevated style={staticStyles.insightCard}>
          <View style={staticStyles.insightHeader}>
            <View
              style={[
                staticStyles.insightIcon,
                { backgroundColor: semantic.accent.tertiarySubtle },
              ]}
            >
              <Ionicons name="analytics-outline" size={20} color={semantic.accent.tertiary} />
            </View>
            <View style={staticStyles.insightCopy}>
              <Text style={[staticStyles.insightTitle, { color: semantic.text.primary }]}>
                Flujo del mes
              </Text>
              <Text style={[staticStyles.insightDescription, { color: semantic.text.secondary }]}>
                La actividad aparecerá aquí cuando empiecen las emisiones.
              </Text>
            </View>
          </View>
          <View style={[staticStyles.progressTrack, { backgroundColor: semantic.chart.track }]}>
            <View
              style={[staticStyles.progressFill, { backgroundColor: semantic.chart.tertiary }]}
            />
          </View>
        </Card>

        <SectionHeader title="Módulos" caption="Suite fiscal" />
        <Card variant="elevated" elevated style={staticStyles.modulesCard}>
          {modulePreview.map((module) => (
            <View
              key={module.title}
              style={[staticStyles.moduleRow, { borderBottomColor: semantic.border.default }]}
            >
              <View
                style={[staticStyles.moduleIcon, { backgroundColor: semantic.accent.altSubtle }]}
              >
                <Ionicons name={module.icon} size={18} color={semantic.accent.alt} />
              </View>
              <View style={staticStyles.moduleCopy}>
                <Text style={[staticStyles.moduleTitle, { color: semantic.text.primary }]}>
                  {module.title}
                </Text>
                <Text style={[staticStyles.moduleSubtitle, { color: semantic.text.secondary }]}>
                  {module.subtitle}
                </Text>
              </View>
              <Ionicons name="time-outline" size={18} color={semantic.text.tertiary} />
            </View>
          ))}
          <View style={staticStyles.moduleFooter}>
            <Text style={[staticStyles.moduleFooterText, { color: semantic.text.secondary }]}>
              Emisión de facturas, notas de crédito, retenciones y guías.
            </Text>
          </View>
        </Card>
      </ScrollView>
    </View>
  )
}

function HeroSignal({ label, value }: { label: string; value: string }) {
  const { semantic } = useTheme()

  return (
    <View style={staticStyles.heroSignal}>
      <Text style={[staticStyles.heroSignalLabel, { color: semantic.text.secondary }]}>
        {label}
      </Text>
      <Text style={[staticStyles.heroSignalValue, { color: semantic.text.primary }]}>{value}</Text>
    </View>
  )
}

function SectionHeader({ title, caption }: { title: string; caption: string }) {
  const { semantic } = useTheme()

  return (
    <View style={staticStyles.sectionHeader}>
      <Text style={[staticStyles.sectionTitle, { color: semantic.text.primary }]}>{title}</Text>
      <Text style={[staticStyles.sectionCaption, { color: semantic.text.secondary }]}>
        {caption}
      </Text>
    </View>
  )
}

function MetricCard({
  icon,
  label,
  value,
  detail,
  tone,
}: {
  icon: keyof typeof Ionicons.glyphMap
  label: string
  value: string
  detail: string
  tone: MetricTone
}) {
  const { semantic } = useTheme()
  const tones: Record<MetricTone, { color: string; bg: string }> = {
    primary: { color: semantic.accent.default, bg: semantic.accent.subtle },
    secondary: { color: semantic.accent.alt, bg: semantic.accent.altSubtle },
    error: { color: semantic.status.error, bg: semantic.status.errorBg },
  }
  const palette = tones[tone]

  return (
    <Card variant="elevated" elevated style={staticStyles.metricCard}>
      <View style={[staticStyles.metricIcon, { backgroundColor: palette.bg }]}>
        <Ionicons name={icon} size={20} color={palette.color} />
      </View>
      <View style={staticStyles.metricCopy}>
        <Text style={[staticStyles.metricValue, { color: semantic.text.primary }]}>{value}</Text>
        <Text
          style={[staticStyles.metricLabel, { color: semantic.text.primary }]}
          numberOfLines={2}
        >
          {label}
        </Text>
        <Text style={[staticStyles.metricDetail, { color: semantic.text.secondary }]}>
          {detail}
        </Text>
      </View>
    </Card>
  )
}

const staticStyles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], gap: spacing[5], paddingBottom: spacing[12] },
  hero: {
    borderRadius: radius['2xl'],
    borderWidth: 1,
    padding: spacing[5],
    gap: spacing[6],
    overflow: 'hidden',
    ...shadow.lg,
  },
  heroAccent: { position: 'absolute', left: 0, top: 0, bottom: 0, width: 4 },
  heroTop: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: radius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { fontSize: typography.size.xl, fontWeight: typography.weight.bold },
  identity: { flex: 1, minWidth: 0, gap: spacing[1] },
  kicker: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  email: { fontSize: typography.size.base, fontWeight: typography.weight.semibold },
  rolePill: {
    maxWidth: 118,
    borderWidth: 1,
    borderRadius: radius.full,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
  },
  roleText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  heroCopy: { gap: spacing[2] },
  heroTitle: {
    fontSize: typography.size['3xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['3xl'] * typography.lineHeight.tight,
  },
  heroSubtitle: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.normal,
  },
  heroFooter: { borderTopWidth: 1, flexDirection: 'row', paddingTop: spacing[4], gap: spacing[3] },
  heroSignal: { flex: 1, gap: spacing[1] },
  heroSignalLabel: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  heroSignalValue: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  sectionHeader: { gap: spacing[1] },
  sectionTitle: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  sectionCaption: { fontSize: typography.size.sm },
  metricGrid: { gap: spacing[3] },
  metricCard: { flexDirection: 'row', alignItems: 'center', gap: spacing[4] },
  metricIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  metricCopy: { flex: 1, gap: spacing[1] },
  metricValue: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['2xl'] * typography.lineHeight.tight,
  },
  metricLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  metricDetail: { fontSize: typography.size.xs },
  insightCard: { gap: spacing[4] },
  insightHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  insightIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  insightCopy: { flex: 1, minWidth: 0, gap: spacing[1] },
  insightTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  insightDescription: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
  progressTrack: { height: 8, borderRadius: radius.full, overflow: 'hidden' },
  progressFill: { width: 0, height: '100%' },
  modulesCard: { paddingBottom: 0 },
  moduleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
  },
  moduleIcon: {
    width: 40,
    height: 40,
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  moduleCopy: { flex: 1, minWidth: 0, gap: spacing[1] },
  moduleTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  moduleSubtitle: { fontSize: typography.size.xs },
  moduleFooter: { paddingVertical: spacing[4] },
  moduleFooterText: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
})
