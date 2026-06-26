import React, { useState } from 'react'
import { FlatList, StyleSheet, View } from 'react-native'
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
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { CreditNoteEligibleInvoiceItem } from '../components/CreditNoteEligibleInvoiceItem'
import { useDocuments } from '../hooks/useDocuments'
import type { DocumentListFilters } from '../types'

const ELIGIBLE_BASE_FILTERS: DocumentListFilters = { doc_type: '01', status: 'AUTHORIZED' }

/**
 * Modulo independiente "Notas de Credito": lista facturas autorizadas (elegibles) en
 * vez de vivir como boton dentro de Documentos. Tocar "Acreditar" en una fila navega
 * al formulario parcial existente (`documents/credit-note.tsx`) con esa factura
 * preseleccionada. La anulacion 100% NO vive aqui — sigue siendo una accion de
 * Documentos (ver AnnulInvoiceModal).
 */
export function CreditNoteInvoicesListScreen() {
  const router = useRouter()
  const { semantic } = useTheme()
  const user = useAuthStore(selectUser)
  const canCreate = canWrite(user?.role ?? null)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<DocumentListFilters>(ELIGIBLE_BASE_FILTERS)
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

  if (loading && documents.length === 0) {
    return <LoadingSpinner fullScreen label="Cargando facturas..." />
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

  function applySearch(q: string) {
    setFilters({ ...ELIGIBLE_BASE_FILTERS, q: q || undefined })
  }

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar
        title="Notas de crédito"
        subtitle={
          documents.length
            ? `Página ${page} · ${documents.length} facturas`
            : 'Acredita una factura autorizada'
        }
      />

      <FlatList
        data={documents}
        keyExtractor={(document) => document.document_id}
        renderItem={({ item }) => (
          <CreditNoteEligibleInvoiceItem
            document={item}
            canCreate={canCreate}
            onPress={() =>
              router.push(Routes.tenant.documentCreditNoteNew({ parent: item.document_id }) as Href)
            }
          />
        )}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.header}>
            <ListScreenHeader
              icon="receipt-outline"
              kicker="Comprobantes electrónicos"
              heading="Elige la factura a acreditar"
            />

            <SearchInput
              leftIcon="search-outline"
              placeholder="Serie, cédula/RUC o nombre"
              value={search}
              onChangeText={setSearch}
              onSearchChange={applySearch}
              onSubmitEditing={() => applySearch(search)}
            />

            {error ? <ApiErrorBanner error={error} /> : null}

            <ListPaginationControls {...paginationProps} />
          </View>
        }
        ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
        ListEmptyComponent={
          <EmptyState
            icon="receipt-outline"
            title="Sin facturas para acreditar"
            description="No hay facturas autorizadas que coincidan con la búsqueda."
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
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: { padding: spacing[4], paddingBottom: spacing[12] },
  header: { gap: spacing[4], marginBottom: spacing[4] },
  paginatorBottom: { marginTop: spacing[4] },
})
