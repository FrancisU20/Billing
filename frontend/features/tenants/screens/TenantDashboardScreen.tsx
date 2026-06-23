import React from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing, radius } from '@/constants/tokens'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useNow } from '@/lib/hooks/useNow'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { ecuadorDateTimeDisplay } from '@/lib/utils/ecuador-time'
import { useAuthStore, selectUser } from '@/features/auth/store'
import { Routes } from '@/constants/routes'
import { useDocumentsSummary } from '@/features/documents/hooks/useDocumentsSummary'
import { CertificateSection } from '../components/CertificateSection'
import { DistributionBar } from '../components/DistributionBar'
import { TrendChart } from '../components/TrendChart'
import { useTenant } from '../hooks/useTenant'

const TOP_CLIENT_BADGE_VARIANTS = ['primary', 'accent', 'success', 'warning', 'neutral'] as const

type MetricTone = 'primary' | 'secondary' | 'success' | 'error'

const modulePreview = [
  {
    icon: 'return-down-back-outline',
    title: 'Notas de crédito',
    subtitle: 'Ajustes y anulaciones',
  },
  { icon: 'shield-checkmark-outline', title: 'Retenciones', subtitle: 'Comprobantes fiscales' },
] as const

export function TenantDashboardScreen() {
  const router = useRouter()
  const user = useAuthStore(selectUser)
  const { semantic } = useTheme()
  const now = useNow()
  const { tenant, loading: tenantLoading, refresh } = useTenant(user?.tenantId ?? null)
  const {
    summary,
    loading: summaryLoading,
    error: summaryError,
    refresh: refreshSummary,
  } = useDocumentsSummary()

  useRefreshOnFocus(refresh)
  useRefreshOnFocus(refreshSummary)

  if (tenantLoading) return <LoadingSpinner fullScreen label="Cargando..." />

  const companyName = tenant?.trade_name ?? 'Mi Empresa'

  const issuedCount = summary?.issued_count ?? 0
  const authorizedCount = summary?.authorized_count ?? 0
  const rejectedCount = summary?.rejected_count ?? 0
  const failedCount = summary?.failed_count ?? 0
  const inProgressCount = (summary?.pending_count ?? 0) + (summary?.processing_count ?? 0)
  const authorizedRate = issuedCount > 0 ? Math.round((authorizedCount / issuedCount) * 100) : 0
  const documentLimit = summary?.document_limit ?? null
  const isUnlimitedPlan = summary?.is_unlimited ?? false
  const isFreePlan = summary?.is_free_plan ?? false
  const limitRate =
    documentLimit && documentLimit > 0
      ? Math.min(100, Math.round((issuedCount / documentLimit) * 100))
      : 0
  const limitToneKey = limitRate >= 100 ? 'error' : limitRate >= 80 ? 'warning' : 'success'
  const limitTone = {
    error: { color: semantic.status.error, bg: semantic.status.errorBg },
    warning: { color: semantic.status.warning, bg: semantic.status.warningBg },
    success: { color: semantic.status.success, bg: semantic.status.successBg },
  }[limitToneKey]
  const periodCaption = summary
    ? `Periodo ${formatCivilDate(summary.period_start)} - ${formatCivilDate(summary.period_end)}`
    : 'Periodo actual'
  const dailyIssuedPoints = (summary?.daily_issued ?? []).map((point) => ({
    date: point.date,
    value: point.count,
  }))
  const averageTicket =
    authorizedCount > 0 ? Number(summary?.authorized_total ?? 0) / authorizedCount : 0
  const topClients = summary?.top_clients ?? []
  const maxTopClientTotal = Math.max(...topClients.map((client) => Number(client.total)), 1)
  const dashboardMetrics = [
    {
      icon: 'document-text-outline',
      label: 'Documentos emitidos',
      value: formatInteger(issuedCount),
      detail: summaryLoading ? 'Actualizando...' : periodCaption,
      tone: 'primary',
    },
    {
      icon: 'checkmark-circle-outline',
      label: 'Autorizados',
      value: formatInteger(authorizedCount),
      detail: `${authorizedRate}% de autorización`,
      tone: 'success',
    },
    {
      icon: 'alert-circle-outline',
      label: 'Con novedad',
      value: formatInteger(rejectedCount + failedCount),
      detail: `${rejectedCount} rechazados · ${failedCount} fallidos`,
      tone: 'error',
    },
    {
      icon: 'cash-outline',
      label: 'Total autorizado',
      value: formatCurrency(summary?.authorized_total ?? '0.00'),
      detail: `${formatInteger(inProgressCount)} en proceso`,
      tone: 'secondary',
    },
  ] as const

  return (
    <View style={[staticStyles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title={companyName} subtitle="Dashboard" />

      <ScrollView contentContainerStyle={staticStyles.scroll} showsVerticalScrollIndicator={false}>
        <View style={staticStyles.welcomeRow}>
          <Text style={[staticStyles.welcomeTitle, { color: semantic.text.primary }]}>
            {user?.email ? `Bienvenido, ${user.email}` : 'Bienvenido'}
          </Text>
          <Text style={[staticStyles.welcomeDate, { color: semantic.text.secondary }]}>
            {ecuadorDateTimeDisplay(now)}
          </Text>
        </View>

        <View style={staticStyles.topRow}>
          <View style={staticStyles.topColumn}>
            <SectionHeader title="Resumen operativo" caption="Actividad del periodo" />
            {summaryError ? <ApiErrorBanner error={summaryError} /> : null}
            <View style={staticStyles.metricGrid}>
              <View style={staticStyles.metricRow}>
                {dashboardMetrics.slice(0, 2).map((metric) => (
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
              <View style={staticStyles.metricRow}>
                {dashboardMetrics.slice(2, 4).map((metric) => (
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
            </View>
          </View>

          <View style={staticStyles.topColumn}>
            <SectionHeader title="Módulos" caption="Suite fiscal" />
            <Card variant="elevated" elevated style={staticStyles.modulesCard}>
              <View
                style={[staticStyles.moduleRow, { borderBottomColor: semantic.border.default }]}
              >
                <View
                  style={[staticStyles.moduleIcon, { backgroundColor: semantic.accent.subtle }]}
                >
                  <Ionicons name="receipt-outline" size={18} color={semantic.accent.default} />
                </View>
                <View style={staticStyles.moduleCopy}>
                  <Text style={[staticStyles.moduleTitle, { color: semantic.text.primary }]}>
                    Facturas
                  </Text>
                  <Text style={[staticStyles.moduleSubtitle, { color: semantic.text.secondary }]}>
                    Emisión SRI habilitada
                  </Text>
                  <View style={staticStyles.moduleActions}>
                    <Button
                      variant="primary"
                      size="sm"
                      onPress={() => router.push(Routes.tenant.documentNew as Href)}
                    >
                      Emitir
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onPress={() => router.push(Routes.tenant.documents as Href)}
                    >
                      Ver documentos
                    </Button>
                  </View>
                </View>
                <Ionicons
                  name="checkmark-circle-outline"
                  size={18}
                  color={semantic.status.success}
                />
              </View>
              {modulePreview.map((module) => (
                <View
                  key={module.title}
                  style={[staticStyles.moduleRow, { borderBottomColor: semantic.border.default }]}
                >
                  <View
                    style={[
                      staticStyles.moduleIcon,
                      { backgroundColor: semantic.accent.altSubtle },
                    ]}
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
                  <View
                    style={[
                      staticStyles.comingSoonPill,
                      { backgroundColor: semantic.bg.muted, borderColor: semantic.border.default },
                    ]}
                  >
                    <Text style={[staticStyles.comingSoonText, { color: semantic.text.tertiary }]}>
                      Próximo
                    </Text>
                  </View>
                </View>
              ))}
              <View style={staticStyles.moduleFooter}>
                <Text style={[staticStyles.moduleFooterText, { color: semantic.text.secondary }]}>
                  Emisión de facturas, notas de crédito, retenciones y guías.
                </Text>
              </View>
            </Card>
          </View>
        </View>

        <View style={staticStyles.topRow}>
          <View style={staticStyles.topColumn}>
            <SectionHeader title="Certificado digital" caption="Estado del certificado p12" />
            {tenant ? (
              <CertificateSection
                tenantId={tenant.id}
                canManage={false}
                style={staticStyles.equalHeightCard}
              />
            ) : (
              <Card variant="elevated" elevated style={staticStyles.equalHeightCard}>
                <LoadingSpinner size="small" compact />
              </Card>
            )}
          </View>

          <View style={staticStyles.topColumn}>
            <SectionHeader title="Evolución diaria" caption="Documentos emitidos por día" />
            <Card
              variant="elevated"
              elevated
              style={[staticStyles.insightCard, staticStyles.equalHeightCard]}
            >
              {dailyIssuedPoints.length > 0 ? (
                <TrendChart data={dailyIssuedPoints} formatValue={formatInteger} />
              ) : (
                <Text style={[staticStyles.insightDescription, { color: semantic.text.secondary }]}>
                  Aún no hay documentos emitidos en el periodo actual.
                </Text>
              )}
            </Card>
          </View>
        </View>

        <View style={staticStyles.topRow}>
          <View style={staticStyles.topColumn}>
            <SectionHeader title="Ticket promedio" caption="Valor medio por documento autorizado" />
            <MetricCard
              icon="pricetag-outline"
              label="Ticket promedio"
              value={formatCurrency(averageTicket.toFixed(2))}
              detail={
                authorizedCount > 0
                  ? `Sobre ${formatInteger(authorizedCount)} documentos autorizados`
                  : 'Sin documentos autorizados todavía'
              }
              tone="secondary"
            />
          </View>

          <View style={staticStyles.topColumn}>
            {isUnlimitedPlan ? (
              <>
                <SectionHeader title="Límite del plan" caption="Uso del plan este mes" />
                <Card
                  variant="elevated"
                  elevated
                  style={[staticStyles.insightCard, staticStyles.equalHeightCard]}
                >
                  <View style={staticStyles.insightHeader}>
                    <View
                      style={[
                        staticStyles.insightIcon,
                        { backgroundColor: semantic.status.successBg },
                      ]}
                    >
                      <Ionicons name="infinite-outline" size={20} color={semantic.status.success} />
                    </View>
                    <View style={staticStyles.insightCopy}>
                      <Text
                        style={[
                          staticStyles.insightDescription,
                          { color: semantic.text.secondary },
                        ]}
                      >
                        {`${formatInteger(issuedCount)} documentos emitidos este mes.`}
                      </Text>
                    </View>
                    <Badge label="Ilimitado" variant="success" size="sm" />
                  </View>
                </Card>
              </>
            ) : documentLimit ? (
              <>
                <SectionHeader title="Límite del plan" caption="Uso del plan este mes" />
                <Card
                  variant="elevated"
                  elevated
                  style={[staticStyles.insightCard, staticStyles.equalHeightCard]}
                >
                  <View style={staticStyles.insightHeader}>
                    <View style={[staticStyles.insightIcon, { backgroundColor: limitTone.bg }]}>
                      <Ionicons name="speedometer-outline" size={20} color={limitTone.color} />
                    </View>
                    <View style={staticStyles.insightCopy}>
                      <Text
                        style={[
                          staticStyles.insightDescription,
                          { color: semantic.text.secondary },
                        ]}
                      >
                        {isFreePlan
                          ? `${formatInteger(issuedCount)} de ${formatInteger(documentLimit)} documentos usados.`
                          : `${formatInteger(issuedCount)} de ${formatInteger(documentLimit)} documentos usados este mes.`}
                      </Text>
                    </View>
                  </View>
                  <View
                    style={[staticStyles.progressTrack, { backgroundColor: semantic.chart.track }]}
                  >
                    <View
                      style={[
                        staticStyles.progressFill,
                        { backgroundColor: limitTone.color, width: `${limitRate}%` },
                      ]}
                    />
                  </View>
                </Card>
              </>
            ) : null}
          </View>
        </View>

        <View style={staticStyles.topColumn}>
          <SectionHeader title="Top clientes" caption="Mayor monto facturado del mes" />
          <Card variant="elevated" elevated>
            {topClients.length > 0 ? (
              <ScrollView
                style={staticStyles.topClientsScroll}
                contentContainerStyle={staticStyles.topClientsList}
                showsVerticalScrollIndicator={false}
              >
                {topClients.map((client, index) => (
                  <DistributionBar
                    key={client.client_id}
                    label={client.name}
                    count={Number(client.total)}
                    total={maxTopClientTotal}
                    variant={TOP_CLIENT_BADGE_VARIANTS[index % TOP_CLIENT_BADGE_VARIANTS.length]}
                    formatValue={(value) => formatCurrency(value.toFixed(2))}
                  />
                ))}
              </ScrollView>
            ) : (
              <Text style={[staticStyles.insightDescription, { color: semantic.text.secondary }]}>
                Aún no hay clientes facturados este mes.
              </Text>
            )}
          </Card>
        </View>
      </ScrollView>
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
    success: { color: semantic.status.success, bg: semantic.status.successBg },
    error: { color: semantic.status.error, bg: semantic.status.errorBg },
  }
  const palette = tones[tone]

  return (
    <Card variant="elevated" elevated style={staticStyles.metricCard}>
      <View style={[staticStyles.metricIcon, { backgroundColor: palette.bg }]}>
        <Ionicons name={icon} size={20} color={palette.color} />
      </View>
      <View style={staticStyles.metricCopy}>
        <Text
          style={[staticStyles.metricLabel, { color: semantic.text.secondary }]}
          numberOfLines={2}
        >
          {label}
        </Text>
        <Text style={[staticStyles.metricValue, { color: semantic.text.primary }]}>{value}</Text>
        <Text style={[staticStyles.metricDetail, { color: semantic.text.secondary }]}>
          {detail}
        </Text>
      </View>
    </Card>
  )
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat('es-EC', { maximumFractionDigits: 0 }).format(value)
}

function formatCurrency(value: string): string {
  const amount = Number(value)
  return new Intl.NumberFormat('es-EC', {
    currency: 'USD',
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
    style: 'currency',
  }).format(Number.isFinite(amount) ? amount : 0)
}

function formatCivilDate(value: string): string {
  const [year, month, day] = value.split('-')
  return year && month && day ? `${day}/${month}/${year}` : value
}

const staticStyles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], gap: spacing[5], paddingBottom: spacing[12] },
  welcomeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    gap: spacing[2],
  },
  welcomeTitle: { fontSize: typography.size.xl, fontWeight: typography.weight.bold },
  welcomeDate: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  topRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  topColumn: { flexGrow: 1, flexBasis: 420, minWidth: 320, gap: spacing[4] },
  // mismo patron que `equalHeightCard` en CompanyScreen: el card se estira para igualar
  // al mas alto de su fila (stretch por defecto en `topRow`, flexDirection: 'row').
  equalHeightCard: { flex: 1 },
  sectionHeader: { gap: spacing[1] },
  sectionTitle: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  sectionCaption: { fontSize: typography.size.sm },
  // flex:1 hace que el grid llene el alto que `topRow` ya estira para igualar la columna
  // de Modulos (stretch por defecto en un contenedor row); cada fila/card tambien usa
  // flex:1 para repartir ese alto, asi las 4 cards terminan a la misma altura que Modulos.
  metricGrid: { flex: 1, gap: spacing[3] },
  metricRow: { flex: 1, flexDirection: 'row', gap: spacing[3] },
  metricCard: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  metricIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  metricCopy: { flex: 1, minWidth: 0, gap: spacing[1] },
  metricLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  metricValue: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['2xl'] * typography.lineHeight.tight,
  },
  metricDetail: { fontSize: typography.size.xs },
  insightCard: { gap: spacing[4] },
  topClientsScroll: { maxHeight: 280 },
  topClientsList: { gap: spacing[3] },
  insightHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  insightIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
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
  progressFill: { height: '100%' },
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
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  moduleCopy: { flex: 1, minWidth: 0, gap: spacing[1] },
  moduleTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  moduleSubtitle: { fontSize: typography.size.xs },
  moduleActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[2],
    paddingTop: spacing[2],
  },
  comingSoonPill: {
    borderRadius: radius.full,
    borderWidth: 1,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1],
  },
  comingSoonText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  moduleFooter: { paddingVertical: spacing[4] },
  moduleFooterText: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
})
