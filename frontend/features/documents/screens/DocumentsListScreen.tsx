import React, { useCallback, useState } from 'react'
import { FlatList, Linking, StyleSheet, View } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { EmptyState } from '@/components/ui/EmptyState'
import { ListPaginationControls } from '@/components/ui/ListPaginationControls'
import { ListScreenHeader } from '@/components/layout/ListScreenHeader'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { canWrite } from '@/constants/roles'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { documentsApi } from '../api'
import { AnnulInvoiceModal } from '../components/AnnulInvoiceModal'
import { DocumentListItem } from '../components/DocumentListItem'
import { DocumentsFilters } from '../components/DocumentsFilters'
import {
  emptyDocumentFilterDraft,
  toDocumentListFilters,
  type DocumentFilterDraft,
} from '../filters'
import { useDocuments } from '../hooks/useDocuments'
import { getCreditNoteBlockReason } from '../utils'
import type { Document, DocumentListFilters } from '../types'

export function DocumentsListScreen() {
  const router = useRouter()
  const { semantic } = useTheme()
  const user = useAuthStore(selectUser)
  const [draft, setDraft] = useState<DocumentFilterDraft>(emptyDocumentFilterDraft)
  const [filters, setFilters] = useState<DocumentListFilters>({})
  const [annulTarget, setAnnulTarget] = useState<Document | null>(null)
  const {
    documents,
    loading,
    error,
    refresh,
    nextPage,
    previousPage,
    setPageSize,
    page,
    pageSize,
    totalItems,
    totalPages,
    canGoNext,
    canGoPrevious,
  } = useDocuments(filters)
  useRefreshOnFocus(refresh)

  function applyFilters() {
    setFilters(toDocumentListFilters(draft))
  }

  const applySearchFilters = useCallback((nextDraft: DocumentFilterDraft) => {
    setFilters(toDocumentListFilters(nextDraft))
  }, [])

  function resetFilters() {
    setDraft(emptyDocumentFilterDraft)
    setFilters({})
  }

  const { error: downloadError, submit: downloadRide } = useFormSubmit(
    async (documentId: string) => {
      const { url } = await documentsApi.getRideUrl(documentId)
      await Linking.openURL(url)
    },
  )
  const { error: downloadXmlError, submit: downloadXml } = useFormSubmit(
    async (documentId: string) => {
      const { url } = await documentsApi.getXmlUrl(documentId)
      await Linking.openURL(url)
    },
  )

  if (loading && documents.length === 0) {
    return <LoadingSpinner fullScreen label="Cargando documentos..." />
  }

  const paginationProps = {
    page,
    pageSize,
    itemCount: documents.length,
    totalItems,
    totalPages,
    canGoPrevious,
    canGoNext,
    loading,
    onPrevious: previousPage,
    onNext: nextPage,
    onPageSizeChange: setPageSize,
  }

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar
        title="Documentos"
        subtitle={
          documents.length
            ? `Página ${page} · ${documents.length} registros`
            : 'Facturación electrónica'
        }
      />

      <FlatList
        data={documents}
        keyExtractor={(document) => document.document_id}
        renderItem={({ item }) => (
          <DocumentListItem
            document={item}
            onView={() => router.push(Routes.tenant.documentDetail(item.document_id) as Href)}
            onDownloadRide={() => downloadRide(item.document_id)}
            onDownloadXml={() => downloadXml(item.document_id)}
            canAnnul={canWrite(user?.role ?? null)}
            annulDisabledReason={getCreditNoteBlockReason(item)}
            onAnnul={() => setAnnulTarget(item)}
          />
        )}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.header}>
            <ListScreenHeader
              icon="document-text-outline"
              kicker="Comprobantes electrónicos"
              heading="Facturas emitidas al SRI"
              action={{
                label: 'Emitir documento',
                onPress: () => router.push(Routes.tenant.documentNew as Href),
              }}
            />

            <DocumentsFilters
              value={draft}
              onChange={setDraft}
              onApply={applyFilters}
              onReset={resetFilters}
              onSearchApply={applySearchFilters}
            />

            {error ? <ApiErrorBanner error={error} /> : null}
            {downloadError ? <ApiErrorBanner error={downloadError} /> : null}
            {downloadXmlError ? <ApiErrorBanner error={downloadXmlError} /> : null}

            <ListPaginationControls {...paginationProps} />
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
          <View style={styles.paginatorBottom}>
            <ListPaginationControls {...paginationProps} />
          </View>
        }
        refreshing={loading}
        onRefresh={refresh}
        showsVerticalScrollIndicator={false}
      />

      <AnnulInvoiceModal
        visible={!!annulTarget}
        document={annulTarget}
        onClose={() => setAnnulTarget(null)}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: { padding: spacing[4], paddingBottom: spacing[12] },
  header: { gap: spacing[4], marginBottom: spacing[4] },
  paginatorBottom: { marginTop: spacing[4] },
})
