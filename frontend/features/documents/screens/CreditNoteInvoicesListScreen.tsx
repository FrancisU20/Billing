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
import { SearchInput } from '@/components/ui/SearchInput'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { canWrite } from '@/constants/roles'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { documentsApi } from '../api'
import { DocumentListItem } from '../components/DocumentListItem'
import { InvoicePickerModal } from '../components/InvoicePickerModal'
import { useDocuments } from '../hooks/useDocuments'
import { useRetryDocument } from '../hooks/useRetryDocument'
import type { Document, DocumentListFilters } from '../types'

// Modulo independiente "Notas de Credito" — lista las NC ya emitidas (cualquier
// status, para que las rechazadas sean visibles y se puedan reintentar). Fijo, igual
// patron que FACTURA_ONLY_FILTERS en DocumentsListScreen.
const CREDIT_NOTE_ONLY_FILTERS: DocumentListFilters = { doc_type: '04' }

/**
 * Modulo independiente "Notas de Credito": lista las NC ya emitidas/rechazadas (ya no
 * lista facturas elegibles — eso ahora es un picker aparte). Botón "Crear nota de
 * crédito" abre `InvoicePickerModal` (factura autorizada a acreditar) y navega al
 * formulario parcial existente (`documents/credit-note.tsx`). La anulación 100% NO
 * vive aquí — sigue siendo una acción de Documentos (ver AnnulInvoiceModal).
 */
export function CreditNoteInvoicesListScreen() {
  const router = useRouter()
  const { semantic } = useTheme()
  const user = useAuthStore(selectUser)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<DocumentListFilters>(CREDIT_NOTE_ONLY_FILTERS)
  const [pickerOpen, setPickerOpen] = useState(false)
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
  const { error: retryError, submit: retryDocument } = useRetryDocument(refresh)

  function applySearch(q: string) {
    setFilters({ ...CREDIT_NOTE_ONLY_FILTERS, q: q || undefined })
  }

  const applySearchImmediate = useCallback((q: string) => {
    setFilters({ ...CREDIT_NOTE_ONLY_FILTERS, q: q || undefined })
  }, [])

  if (loading && documents.length === 0) {
    return <LoadingSpinner fullScreen label="Cargando notas de crédito..." />
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
        title="Notas de crédito"
        subtitle={
          documents.length
            ? `Página ${page} · ${documents.length} registros`
            : 'Acreditaciones emitidas al SRI'
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
            canRetry={canWrite(user?.role ?? null)}
            onRetry={() => retryDocument(item.document_id)}
          />
        )}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.header}>
            <ListScreenHeader
              icon="receipt-outline"
              kicker="Comprobantes electrónicos"
              heading="Notas de crédito emitidas al SRI"
              action={{
                label: 'Crear nota de crédito',
                onPress: () => setPickerOpen(true),
              }}
            />

            <SearchInput
              leftIcon="search-outline"
              placeholder="Serie, cédula/RUC o nombre"
              value={search}
              onChangeText={setSearch}
              onSearchChange={applySearchImmediate}
              onSubmitEditing={() => applySearch(search)}
            />

            {error ? <ApiErrorBanner error={error} /> : null}
            {downloadError ? <ApiErrorBanner error={downloadError} /> : null}
            {downloadXmlError ? <ApiErrorBanner error={downloadXmlError} /> : null}
            {retryError ? <ApiErrorBanner error={retryError} /> : null}

            <ListPaginationControls {...paginationProps} />
          </View>
        }
        ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
        ListEmptyComponent={
          <EmptyState
            icon="receipt-outline"
            title="Sin notas de crédito"
            description="No hay notas de crédito que coincidan con la búsqueda."
            action={{ label: 'Crear nota de crédito', onPress: () => setPickerOpen(true) }}
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

      <InvoicePickerModal
        visible={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={(document: Document) => {
          setPickerOpen(false)
          router.push(Routes.tenant.documentCreditNoteNew({ parent: document.document_id }) as Href)
        }}
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
