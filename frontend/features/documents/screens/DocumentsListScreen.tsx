import React, { useCallback, useState } from 'react'
import { FlatList, Linking, StyleSheet, View } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { FormField } from '@/components/ui/FormField'
import { ListPaginationControls } from '@/components/ui/ListPaginationControls'
import { ListScreenHeader } from '@/components/layout/ListScreenHeader'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { canWrite } from '@/constants/roles'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { documentsApi } from '../api'
import { DocumentListItem } from '../components/DocumentListItem'
import { DocumentsFilters } from '../components/DocumentsFilters'
import {
  emptyDocumentFilterDraft,
  toDocumentListFilters,
  type DocumentFilterDraft,
} from '../filters'
import { useDocuments } from '../hooks/useDocuments'
import { getAnnulBlockReason } from '../utils'
import type { Document, DocumentListFilters } from '../types'

export function DocumentsListScreen() {
  const router = useRouter()
  const { semantic } = useTheme()
  const toast = useToast()
  const user = useAuthStore(selectUser)
  const [draft, setDraft] = useState<DocumentFilterDraft>(emptyDocumentFilterDraft)
  const [filters, setFilters] = useState<DocumentListFilters>({})
  const [annulDocument, setAnnulDocument] = useState<Document | null>(null)
  const [annulReason, setAnnulReason] = useState('')
  const [annulReasonError, setAnnulReasonError] = useState<string | null>(null)
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
  const {
    submitting: annulling,
    error: annulError,
    submit: confirmAnnul,
  } = useFormSubmit(async (document: Document, reason: string) => {
    await documentsApi.annul(
      document.document_id,
      reason.trim(),
      createIdempotencyKey('document_annul'),
    )
    toast.success('Documento marcado como anulado')
    setAnnulDocument(null)
    setAnnulReason('')
    setAnnulReasonError(null)
    await refresh()
  })

  function closeAnnulDialog() {
    setAnnulDocument(null)
    setAnnulReason('')
    setAnnulReasonError(null)
  }

  function submitAnnulDialog() {
    if (!annulDocument) return
    if (!annulReason.trim()) {
      setAnnulReasonError('Indica el motivo de la anulación.')
      return
    }
    setAnnulReasonError(null)
    confirmAnnul(annulDocument, annulReason)
  }

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
            annulDisabledReason={getAnnulBlockReason(item)}
            onAnnul={() => setAnnulDocument(item)}
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

      <ConfirmDialog
        visible={annulDocument !== null}
        title="Anular factura"
        message="Esta acción no se puede revertir. El trámite de anulación ante el SRI se hace por fuera de Wali (portal SRI en línea o Facturador SRI) — marca esto como anulado solo después de completarlo ahí."
        confirmLabel="Marcar como anulado"
        variant="danger"
        icon="ban-outline"
        isLoading={annulling}
        confirmDisabled={!annulReason.trim()}
        onCancel={closeAnnulDialog}
        onConfirm={submitAnnulDialog}
      >
        <FormField
          label="Motivo de la anulación"
          placeholder="Ej. error en el monto facturado"
          leftIcon="alert-circle-outline"
          error={annulReasonError ?? undefined}
          onChangeText={(value) => {
            setAnnulReason(value)
            setAnnulReasonError(null)
          }}
          value={annulReason}
          required
        />
        {annulError ? <ApiErrorBanner error={annulError} /> : null}
      </ConfirmDialog>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: { padding: spacing[4], paddingBottom: spacing[12] },
  header: { gap: spacing[4], marginBottom: spacing[4] },
  paginatorBottom: { marginTop: spacing[4] },
})
