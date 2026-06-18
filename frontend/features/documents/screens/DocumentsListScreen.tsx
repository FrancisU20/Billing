import React, { useState } from 'react'
import { FlatList, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing, typography } from '@/constants/tokens'
import { DocumentListItem } from '../components/DocumentListItem'
import {
  DocumentsFilters,
  emptyDocumentFilterDraft,
  toDocumentListFilters,
  type DocumentFilterDraft,
} from '../components/DocumentsFilters'
import { useDocuments } from '../hooks/useDocuments'
import type { DocumentListFilters } from '../types'

export function DocumentsListScreen() {
  const router = useRouter()
  const { semantic } = useTheme()
  const [draft, setDraft] = useState<DocumentFilterDraft>(emptyDocumentFilterDraft)
  const [filters, setFilters] = useState<DocumentListFilters>({})
  const { documents, loading, loadingMore, error, refresh, fetchMore } = useDocuments(filters)

  function applyFilters() {
    setFilters(toDocumentListFilters(draft))
  }

  function resetFilters() {
    setDraft(emptyDocumentFilterDraft)
    setFilters({})
  }

  if (loading) return <LoadingSpinner fullScreen label="Cargando documentos..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar
        title="Documentos"
        subtitle={documents.length ? `${documents.length} resultados` : 'Facturación electrónica'}
      />

      <FlatList
        data={documents}
        keyExtractor={(document) => document.document_id}
        renderItem={({ item }) => (
          <DocumentListItem
            document={item}
            onView={() => router.push(Routes.tenant.documentDetail(item.document_id) as Href)}
          />
        )}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.header}>
            <View style={styles.heroRow}>
              <View style={styles.heroCopy}>
                <View style={styles.kickerRow}>
                  <Ionicons
                    name="document-text-outline"
                    size={16}
                    color={semantic.accent.default}
                  />
                  <Text style={[styles.kicker, { color: semantic.accent.default }]}>
                    Comprobantes electrónicos
                  </Text>
                </View>
                <Text style={[styles.heading, { color: semantic.text.primary }]}>
                  Facturas emitidas al SRI
                </Text>
              </View>
              <Button
                variant="primary"
                size="md"
                onPress={() => router.push(Routes.tenant.documentNew as Href)}
              >
                Emitir documento
              </Button>
            </View>

            <DocumentsFilters
              value={draft}
              onChange={setDraft}
              onApply={applyFilters}
              onReset={resetFilters}
            />

            {error ? <ApiErrorBanner error={error} /> : null}
          </View>
        }
        ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
        ListEmptyComponent={
          <EmptyState
            icon="document-text-outline"
            title="Sin documentos"
            description="No hay documentos que coincidan con los filtros actuales."
            action={{
              label: 'Emitir documento',
              onPress: () => router.push(Routes.tenant.documentNew as Href),
            }}
          />
        }
        ListFooterComponent={
          loadingMore ? (
            <View style={styles.loadingMore}>
              <LoadingSpinner size="small" compact />
            </View>
          ) : null
        }
        onEndReached={fetchMore}
        onEndReachedThreshold={0.3}
        refreshing={loading}
        onRefresh={refresh}
        showsVerticalScrollIndicator={false}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: { padding: spacing[4], paddingBottom: spacing[12] },
  header: { gap: spacing[4], marginBottom: spacing[4] },
  heroRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[4],
    justifyContent: 'space-between',
  },
  heroCopy: { flex: 1, gap: spacing[1], minWidth: 260 },
  kickerRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[1] },
  kicker: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
    textTransform: 'uppercase',
  },
  heading: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['2xl'] * 1.2,
  },
  loadingMore: { paddingVertical: spacing[5] },
})
