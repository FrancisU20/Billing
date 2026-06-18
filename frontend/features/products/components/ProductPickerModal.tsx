import React, { useState } from 'react'
import { FlatList, Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { useTheme } from '@/lib/theme-context'
import { overlay, radius, spacing, typography } from '@/constants/tokens'
import { productsApi } from '../api'
import type { Product, ProductIvaRate } from '../types'

interface ProductPickerModalProps {
  visible: boolean
  onClose: () => void
  onSelect: (product: Product) => void
}

export function ProductPickerModal({ visible, onClose, onSelect }: ProductPickerModalProps) {
  const { semantic } = useTheme()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Product[]>([])
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [quickSku, setQuickSku] = useState('')
  const [quickName, setQuickName] = useState('')
  const [quickPrice, setQuickPrice] = useState('0.00')
  const [quickIva, setQuickIva] = useState<ProductIvaRate>('15')

  async function search() {
    const q = query.trim()
    if (!q) return
    setLoading(true)
    setError(null)
    try {
      const page = await productsApi.list({ q, status: 'ACTIVE' })
      setResults(page.items)
      setSearched(true)
    } catch (e) {
      setError(toApiError(e))
    } finally {
      setLoading(false)
    }
  }

  async function createQuick() {
    const sku = quickSku.trim()
    const name = quickName.trim()
    if (!sku || !name) return
    setCreating(true)
    setError(null)
    try {
      const product = await productsApi.create(
        {
          sku,
          name,
          description: name,
          kind: 'PRODUCT',
          unit: 'unit',
          unit_price: quickPrice.trim() || '0.00',
          iva_rate: quickIva,
          stock_enabled: false,
          stock_quantity: null,
          low_stock_threshold: null,
        },
        createIdempotencyKey('product_quick_create'),
      )
      onSelect(product)
    } catch (e) {
      setError(toApiError(e))
    } finally {
      setCreating(false)
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
            <Text style={[styles.title, { color: semantic.text.primary }]}>
              Producto o servicio
            </Text>
            <Pressable onPress={onClose} hitSlop={8} accessibilityLabel="Cerrar">
              <Ionicons name="close-outline" size={22} color={semantic.text.secondary} />
            </Pressable>
          </View>

          <View style={styles.searchRow}>
            <View style={styles.searchInput}>
              <Input
                leftIcon="search-outline"
                placeholder="SKU, nombre o descripción"
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
              keyExtractor={(product) => product.id}
              style={styles.list}
              ListEmptyComponent={
                <Text style={[styles.empty, { color: semantic.text.secondary }]}>
                  {searched ? 'Sin resultados' : 'Busca en tu catálogo o crea rápido abajo'}
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
                    {item.name}
                  </Text>
                  <Text
                    style={[styles.resultMeta, { color: semantic.text.secondary }]}
                    numberOfLines={1}
                  >
                    {item.sku} · IVA {item.iva_rate} · ${Number(item.unit_price).toFixed(2)}
                  </Text>
                </Pressable>
              )}
            />
          )}

          <View style={[styles.quickBox, { borderColor: semantic.border.default }]}>
            <Text style={[styles.quickTitle, { color: semantic.text.primary }]}>
              Creación rápida
            </Text>
            <View style={styles.quickGrid}>
              <View style={styles.quickCol}>
                <FormField
                  label="SKU"
                  placeholder="PROD-001"
                  leftIcon="barcode-outline"
                  value={quickSku}
                  onChangeText={setQuickSku}
                  required
                />
              </View>
              <View style={styles.quickWide}>
                <FormField
                  label="Nombre"
                  placeholder="Producto o servicio"
                  leftIcon="cube-outline"
                  value={quickName}
                  onChangeText={setQuickName}
                  required
                />
              </View>
              <View style={styles.quickCol}>
                <FormField
                  label="Precio"
                  placeholder="0.00"
                  keyboardType="decimal-pad"
                  leftIcon="cash-outline"
                  value={quickPrice}
                  onChangeText={setQuickPrice}
                  required
                />
              </View>
            </View>
            <SegmentedControl
              value={quickIva}
              options={[
                { value: '15', label: 'IVA 15%' },
                { value: '5', label: 'IVA 5%' },
                { value: '0', label: 'IVA 0%' },
                { value: 'EXENTO', label: 'Exento' },
              ]}
              onChange={setQuickIva}
            />
            <Button
              variant="secondary"
              size="md"
              isLoading={creating}
              isDisabled={!quickSku.trim() || !quickName.trim()}
              onPress={createQuick}
            >
              Crear y usar
            </Button>
          </View>
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
    maxHeight: '92%',
    maxWidth: 640,
    padding: spacing[5],
    width: '100%',
  },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  title: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  searchRow: { flexDirection: 'row', gap: spacing[2] },
  searchInput: { flex: 1 },
  list: { maxHeight: 220 },
  empty: { fontSize: typography.size.sm, padding: spacing[4], textAlign: 'center' },
  resultRow: { borderBottomWidth: 1, gap: spacing[1] - 2, padding: spacing[3] },
  resultName: { fontSize: typography.size.base, fontWeight: typography.weight.semibold },
  resultMeta: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.xs },
  quickBox: { borderRadius: radius.md, borderWidth: 1, gap: spacing[3], padding: spacing[3] },
  quickTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  quickCol: { flex: 1, minWidth: 140 },
  quickWide: { flex: 2, minWidth: 220 },
})
