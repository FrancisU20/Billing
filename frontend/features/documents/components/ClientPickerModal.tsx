import React, { useState } from 'react'
import { FlatList, Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { clientsApi } from '@/features/clients/api'
import type { Client } from '@/features/clients/types'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { useTheme } from '@/lib/theme-context'
import { overlay, radius, spacing, typography } from '@/constants/tokens'

interface ClientPickerModalProps {
  visible: boolean
  onClose: () => void
  onSelect: (client: Client) => void
}

export function ClientPickerModal({ visible, onClose, onSelect }: ClientPickerModalProps) {
  const { semantic } = useTheme()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Client[]>([])
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  async function search() {
    const q = query.trim()
    if (!q) return
    setLoading(true)
    setError(null)
    try {
      const page = await clientsApi.list({ q })
      setResults(page.items)
      setSearched(true)
    } catch (e) {
      setError(toApiError(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal transparent visible={visible} animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View
          style={[
            styles.dialog,
            { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
          ]}
        >
          <View style={styles.header}>
            <Text style={[styles.title, { color: semantic.text.primary }]}>Buscar cliente</Text>
            <Pressable onPress={onClose} hitSlop={8} accessibilityLabel="Cerrar">
              <Ionicons name="close-outline" size={22} color={semantic.text.secondary} />
            </Pressable>
          </View>

          <View style={styles.searchRow}>
            <View style={styles.searchInput}>
              <Input
                leftIcon="search-outline"
                placeholder="Razón social, nombre comercial o identificación"
                value={query}
                onChangeText={setQuery}
                onSubmitEditing={search}
                autoFocus
              />
            </View>
            <Button variant="primary" size="md" isLoading={loading} onPress={search}>
              Buscar
            </Button>
          </View>

          {error ? <ApiErrorBanner error={error} /> : null}

          {loading ? (
            <LoadingSpinner compact label="Buscando..." />
          ) : (
            <FlatList
              data={results}
              keyExtractor={(client) => client.id}
              style={styles.list}
              ListEmptyComponent={
                <Text style={[styles.empty, { color: semantic.text.secondary }]}>
                  {searched ? 'Sin resultados' : 'Escribe para buscar'}
                </Text>
              }
              renderItem={({ item }) => (
                <Pressable
                  onPress={() => onSelect(item)}
                  style={({ pressed }) => [
                    styles.resultRow,
                    {
                      backgroundColor: pressed ? semantic.bg.secondary : 'transparent',
                      borderColor: semantic.border.default,
                    },
                  ]}
                >
                  <Text
                    style={[styles.resultName, { color: semantic.text.primary }]}
                    numberOfLines={1}
                  >
                    {item.trade_name || item.legal_name}
                  </Text>
                  <Text
                    style={[styles.resultMeta, { color: semantic.text.secondary }]}
                    numberOfLines={1}
                  >
                    {item.identification}
                  </Text>
                </Pressable>
              )}
            />
          )}
        </View>
      </View>
    </Modal>
  )
}

const styles = StyleSheet.create({
  overlay: {
    alignItems: 'center',
    backgroundColor: overlay.surface.backdrop,
    flex: 1,
    justifyContent: 'center',
    padding: spacing[5],
  },
  dialog: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    maxHeight: '80%',
    maxWidth: 480,
    padding: spacing[5],
    width: '100%',
  },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  title: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  searchRow: { flexDirection: 'row', gap: spacing[2] },
  searchInput: { flex: 1 },
  list: { maxHeight: 320 },
  empty: { fontSize: typography.size.sm, padding: spacing[4], textAlign: 'center' },
  resultRow: { borderBottomWidth: 1, gap: spacing[1] - 2, padding: spacing[3] },
  resultName: { fontSize: typography.size.base, fontWeight: typography.weight.semibold },
  resultMeta: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.xs },
})
