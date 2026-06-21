import React from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { Button } from '@/components/ui/Button'
import { DetailField, DetailSection } from '@/components/ui/DetailSection'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { formatRuc } from '@/lib/utils/format'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { canWrite } from '@/constants/roles'
import { radius, spacing, typography } from '@/constants/tokens'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { CertificateSection } from '../components/CertificateSection'
import { TENANT_ENVIRONMENT_LABELS } from '../constants'
import { useTenant } from '../hooks/useTenant'

export function CompanyScreen() {
  const router = useRouter()
  const { semantic } = useTheme()
  const user = useAuthStore(selectUser)
  const tenantId = user?.tenantId ?? null
  const canManage = canWrite(user?.role ?? null)
  const { tenant, loading, refresh } = useTenant(tenantId)

  useRefreshOnFocus(refresh)

  if (loading) return <LoadingSpinner fullScreen label="Cargando empresa..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Mi empresa" subtitle="Configuración del tenant" canGoBack />

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {tenant ? (
          <>
            <View style={styles.sectionHeader}>
              {canManage ? (
                <Button
                  variant="outline"
                  size="sm"
                  onPress={() => router.push(Routes.tenant.companyEdit as Href)}
                >
                  Editar datos
                </Button>
              ) : null}
            </View>

            <DetailSection title="Datos de empresa" icon="briefcase-outline">
              <DetailField label="Nombre comercial" value={tenant.trade_name} />
              <DetailField label="Razón social" value={tenant.legal_name} />
              <DetailField label="RUC" value={formatRuc(tenant.ruc)} mono />
              <DetailField label="Representante legal" value={tenant.legal_rep_name} />
              <DetailField label="Email" value={tenant.email} />
              <DetailField label="Teléfono" value={tenant.phone} />
              <DetailField label="Dirección" value={tenant.address} />
              <DetailField
                label="Ambiente SRI"
                value={TENANT_ENVIRONMENT_LABELS[tenant.sri_environment]}
              />
            </DetailSection>

            <View style={styles.widgetsRow}>
              <View style={styles.widgetColumn}>
                <CertificateSection
                  tenantId={tenant.id}
                  canManage={canManage}
                  style={styles.equalHeightCard}
                />
              </View>

              <View style={styles.widgetColumn}>
                <DetailSection
                  title="Configuración"
                  icon="settings-outline"
                  layout="stack"
                  style={styles.equalHeightCard}
                >
                  <SettingsRow
                    icon="storefront-outline"
                    title="Establecimientos"
                    subtitle="Puntos de emisión y secuenciales SRI"
                    onPress={() => router.push(Routes.tenant.establishments as Href)}
                  />
                  <SettingsRow
                    icon="pricetag-outline"
                    title="Descuento global"
                    subtitle="Campaña de descuento por tenant"
                    onPress={() => router.push(Routes.tenant.discountCampaign as Href)}
                  />
                  <SettingsRow
                    icon="card-outline"
                    title="Suscripción"
                    subtitle="Facturación y pagos"
                    onPress={() => router.push(Routes.tenant.billing as Href)}
                    last
                  />
                </DetailSection>
              </View>
            </View>
          </>
        ) : null}
      </ScrollView>
    </View>
  )
}

function SettingsRow({
  icon,
  title,
  subtitle,
  onPress,
  last = false,
}: {
  icon: keyof typeof Ionicons.glyphMap
  title: string
  subtitle: string
  onPress: () => void
  last?: boolean
}) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.row,
        !last && { borderBottomWidth: 1, borderBottomColor: semantic.border.default },
      ]}
    >
      <View style={[styles.rowIcon, { backgroundColor: semantic.accent.subtle }]}>
        <Ionicons name={icon} size={18} color={semantic.accent.default} />
      </View>
      <View style={styles.rowCopy}>
        <Text style={[styles.rowTitle, { color: semantic.text.primary }]}>{title}</Text>
        <Text style={[styles.rowSubtitle, { color: semantic.text.secondary }]}>{subtitle}</Text>
      </View>
      <Button variant="ghost" size="sm" onPress={onPress}>
        Abrir
      </Button>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], gap: spacing[4], paddingBottom: spacing[12] },
  sectionHeader: { alignItems: 'flex-end' },
  widgetsRow: { alignItems: 'stretch', flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  widgetColumn: { flexGrow: 1, flexBasis: 320, minWidth: 320 },
  equalHeightCard: { flex: 1 },
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing[3],
    paddingVertical: spacing[3],
  },
  rowIcon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  rowCopy: { flex: 1, gap: spacing[1], minWidth: 0 },
  rowTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  rowSubtitle: { fontSize: typography.size.xs },
})
