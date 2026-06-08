import React, { useCallback, useEffect } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { useLocalSearchParams } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing, radius } from '@/constants/tokens'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Card } from '@/components/ui/Card'
import { Divider } from '@/components/ui/Divider'
import { TenantStatusBadge } from '@/features/tenants/components/TenantStatusBadge'
import { useAsync } from '@/lib/hooks/useAsync'
import { tenantsApi } from '@/features/tenants/api'
import { formatDate, formatRuc } from '@/lib/utils/format'

export default function TenantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { semantic } = useTheme()

  const fetchTenant = useCallback(() => tenantsApi.getById(id), [id])
  const { data: tenant, loading, error, execute } = useAsync(fetchTenant)

  useEffect(() => {
    execute()
  }, [execute])

  if (loading) return <LoadingSpinner fullScreen label="Cargando empresa..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title={tenant?.business_name ?? '—'} canGoBack />

      <ScrollView contentContainerStyle={styles.scroll}>
        {tenant ? (
          <>
            <Card elevated>
              <View style={styles.headerCard}>
                <View style={[styles.avatar, { backgroundColor: semantic.accent.subtle }]}>
                  <Text style={[styles.avatarText, { color: semantic.accent.default }]}>
                    {tenant.business_name.charAt(0).toUpperCase()}
                  </Text>
                </View>
                <View style={styles.headerInfo}>
                  <Text style={[styles.businessName, { color: semantic.text.primary }]}>{tenant.business_name}</Text>
                  {tenant.trade_name ? (
                    <Text style={[styles.tradeName, { color: semantic.text.secondary }]}>{tenant.trade_name}</Text>
                  ) : null}
                  <TenantStatusBadge status={tenant.status} />
                </View>
              </View>
            </Card>

            <Card>
              <Text style={[styles.sectionTitle, { color: semantic.text.secondary }]}>Información fiscal</Text>
              <Divider />
              <View style={styles.fields}>
                <Field label="RUC" value={formatRuc(tenant.ruc)} mono />
                <Field label="Email" value={tenant.email} />
                <Field label="Teléfono" value={tenant.phone} />
                <Field label="Dirección" value={tenant.address} />
              </View>
            </Card>

            <Card>
              <Text style={[styles.sectionTitle, { color: semantic.text.secondary }]}>Metadata</Text>
              <Divider />
              <View style={styles.fields}>
                <Field label="ID" value={tenant.id} mono />
                <Field label="Creado" value={formatDate(tenant.created_at)} />
                <Field label="Actualizado" value={formatDate(tenant.updated_at)} />
              </View>
            </Card>
          </>
        ) : error ? (
          <Text style={[styles.errorText, { color: semantic.status.error }]}>{error.message}</Text>
        ) : null}
      </ScrollView>
    </View>
  )
}

function Field({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  const { semantic } = useTheme()

  return (
    <View style={fieldStyles.container}>
      <Text style={[fieldStyles.label, { color: semantic.text.secondary }]}>{label}</Text>
      <Text style={[fieldStyles.value, mono && fieldStyles.mono, { color: semantic.text.primary }]}>{value}</Text>
    </View>
  )
}

const fieldStyles = StyleSheet.create({
  container: { gap: 3 },
  label: {
    fontSize: typography.size.xs,
    textTransform: 'uppercase',
  },
  value: { fontSize: typography.size.base },
  mono: { fontFamily: 'Courier', fontSize: typography.size.sm },
})

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[4], gap: spacing[4], paddingBottom: spacing[10] },
  headerCard: { flexDirection: 'row', alignItems: 'center', gap: spacing[4] },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
  },
  headerInfo: { flex: 1, gap: spacing[1] },
  businessName: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.bold,
  },
  tradeName: { fontSize: typography.size.sm },
  sectionTitle: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
    marginBottom: spacing[3],
  },
  fields: { gap: spacing[4], marginTop: spacing[3] },
  errorText: {
    textAlign: 'center',
    marginTop: spacing[8],
  },
})
