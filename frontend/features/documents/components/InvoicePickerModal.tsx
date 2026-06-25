import React, { useEffect, useRef, useState } from 'react'
import { StyleSheet, Text } from 'react-native'
import { PickerModal, PickerResultRow } from '@/components/ui/PickerModal'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { useTheme } from '@/lib/theme-context'
import { formatDate } from '@/lib/utils/format'
import { spacing, typography } from '@/constants/tokens'
import { documentsApi } from '../api'
import type { Document } from '../types'

interface InvoicePickerModalProps {
  visible: boolean
  onClose: () => void
  onSelect: (document: Document) => void
}

/**
 * Selector de factura propia AUTORIZADA para acreditar con una Nota de Credito.
 * Modelado sobre ClientPickerModal/PickerModal, pero sin "crear rapido" — aqui solo se
 * puede elegir una factura ya existente, nunca crear una nueva desde este flujo.
 */
export function InvoicePickerModal({ visible, onClose, onSelect }: InvoicePickerModalProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Document[]>([])
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const searchRequestId = useRef(0)

  useEffect(() => {
    if (!visible) return
    searchRequestId.current += 1
    setQuery('')
    setResults([])
    setSearched(false)
    setLoading(false)
    setError(null)
  }, [visible])

  function close() {
    onClose()
  }

  async function search(nextQuery = query) {
    const q = nextQuery.trim()
    if (q.length < 3) return
    const requestId = searchRequestId.current + 1
    searchRequestId.current = requestId
    setLoading(true)
    setError(null)
    try {
      const page = await documentsApi.list({ status: 'AUTHORIZED', doc_type: '01', q })
      if (requestId !== searchRequestId.current) return
      setResults(page.items)
      setSearched(true)
    } catch (e) {
      if (requestId !== searchRequestId.current) return
      setError(toApiError(e))
    } finally {
      if (requestId === searchRequestId.current) {
        setLoading(false)
      }
    }
  }

  return (
    <PickerModal
      visible={visible}
      onClose={close}
      title="Buscar factura a acreditar"
      searchPlaceholder="Serie, comprador o clave de acceso"
      searchValue={query}
      onSearchChangeText={setQuery}
      onSearchChange={(nextQuery) => {
        if (!nextQuery) {
          setResults([])
          setSearched(false)
          return
        }
        void search(nextQuery)
      }}
      onSearchSubmit={() => search()}
      searchLoading={loading}
      error={error}
      results={results}
      keyExtractor={(document) => document.document_id}
      maxDialogWidth={640}
      emptyState={<EmptyResults searched={searched} />}
      renderItem={(document) => (
        <PickerResultRow onPress={() => onSelect(document)}>
          <InvoiceResult document={document} />
        </PickerResultRow>
      )}
    />
  )
}

function EmptyResults({ searched }: { searched: boolean }) {
  const { semantic } = useTheme()
  return (
    <Text style={[styles.empty, { color: semantic.text.secondary }]}>
      {searched
        ? 'Sin facturas autorizadas que coincidan con la búsqueda.'
        : 'Escribe para buscar una factura autorizada propia.'}
    </Text>
  )
}

function InvoiceResult({ document }: { document: Document }) {
  const { semantic } = useTheme()
  return (
    <>
      <Text style={[styles.resultName, { color: semantic.text.primary }]} numberOfLines={1}>
        {document.sequential_display} · {document.buyer_name}
      </Text>
      <Text style={[styles.resultMeta, { color: semantic.text.secondary }]} numberOfLines={1}>
        {formatDate(document.issued_at)} · ${document.total}
      </Text>
    </>
  )
}

const styles = StyleSheet.create({
  empty: { fontSize: typography.size.sm, padding: spacing[4], textAlign: 'center' },
  resultName: { fontSize: typography.size.base, fontWeight: typography.weight.semibold },
  resultMeta: { fontSize: typography.size.xs },
})
