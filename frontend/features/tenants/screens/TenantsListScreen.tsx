import React from 'react'
import { ActivityIndicator, FlatList, StyleSheet, View } from 'react-native'
import { useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { spacing } from '@/constants/tokens'
import { Routes } from '@/constants/routes'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { TenantCard } from '../components/TenantCard'
import { useTenants } from '../hooks/useTenants'

export function TenantsListScreen() {
  const router = useRouter()
  const { tenants, loading, loadingMore, error, refresh, fetchMore } = useTenants()
  const { semantic } = useTheme()

  if (loading) return <LoadingSpinner fullScreen label="Cargando empresas..." />

  return (
    <View style={[staticStyles.container, { backgroundColor: semantic.bg.secondary }]}>
      <AppNavBar
        title="Empresas"
        subtitle={tenants.length ? `${tenants.length} registradas` : undefined}
      />

      {error ? (
        <View style={staticStyles.errorWrap}>
          <ApiErrorBanner error={error} />
        </View>
      ) : (
        <FlatList
          data={tenants}
          keyExtractor={(t) => t.id}
          renderItem={({ item }) => (
            <TenantCard
              tenant={item}
              onPress={() => router.push(Routes.superadmin.tenantDetail(item.id))}
            />
          )}
          contentContainerStyle={staticStyles.list}
          ListHeaderComponent={
            <View style={staticStyles.headerActions}>
              <Button
                variant="primary"
                size="md"
                fullWidth
                onPress={() => router.push(Routes.superadmin.tenantNew)}
              >
                Nueva empresa
              </Button>
            </View>
          }
          ListHeaderComponentStyle={staticStyles.listHeader}
          ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
          ListEmptyComponent={
            <EmptyState
              icon="business-outline"
              title="Sin empresas"
              description="Aún no hay empresas registradas."
            />
          }
          ListFooterComponent={
            loadingMore ? (
              <ActivityIndicator color={semantic.accent.default} style={staticStyles.loadingMore} />
            ) : null
          }
          onEndReached={fetchMore}
          onEndReachedThreshold={0.3}
          refreshing={loading}
          onRefresh={refresh}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  )
}

const staticStyles = StyleSheet.create({
  container: { flex: 1 },
  errorWrap: { padding: spacing[5] },
  list: { padding: spacing[4], paddingBottom: spacing[10] },
  listHeader: { marginBottom: spacing[3] },
  headerActions: { gap: spacing[2] },
  loadingMore: { paddingVertical: spacing[5] },
})
