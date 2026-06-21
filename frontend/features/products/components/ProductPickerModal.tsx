import React, { useEffect, useRef, useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { PickerModal, PickerResultRow } from '@/components/ui/PickerModal'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { MoneyField } from '@/components/ui/SpecializedFields'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { ApiError, toApiError, type ApiError as ApiErrorType } from '@/lib/api/errors'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { productsApi } from '../api'
import type { Product, ProductIvaRate } from '../types'

interface ProductPickerModalProps {
  visible: boolean
  onClose: () => void
  onSelect: (product: Product) => void
  campaign?: { active: boolean; percentage: string } | null
}

export function ProductPickerModal({
  visible,
  onClose,
  onSelect,
  campaign = null,
}: ProductPickerModalProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Product[]>([])
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<ApiErrorType | null>(null)
  const [showQuickCreate, setShowQuickCreate] = useState(false)
  const [quickSku, setQuickSku] = useState('')
  const [quickName, setQuickName] = useState('')
  const [quickPrice, setQuickPrice] = useState('0.00')
  const [quickIva, setQuickIva] = useState<ProductIvaRate>('15')
  const searchRequestId = useRef(0)

  useEffect(() => {
    if (!visible) return
    searchRequestId.current += 1
    setQuery('')
    setResults([])
    setSearched(false)
    setLoading(false)
    setCreating(false)
    setError(null)
    setShowQuickCreate(false)
    setQuickSku('')
    setQuickName('')
    setQuickPrice('0.00')
    setQuickIva('15')
  }, [visible])

  function resetState() {
    setQuery('')
    setResults([])
    setSearched(false)
    setLoading(false)
    setCreating(false)
    setError(null)
    setShowQuickCreate(false)
    resetQuickForm()
  }

  function resetQuickForm() {
    setQuickSku('')
    setQuickName('')
    setQuickPrice('0.00')
    setQuickIva('15')
  }

  function close() {
    resetState()
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
      const page = await productsApi.list({ q, status: 'ACTIVE' })
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

  async function createQuick() {
    const sku = quickSku.trim()
    const name = quickName.trim()
    const price = Number(quickPrice)
    if (!sku || !name || !Number.isFinite(price) || price <= 0) return
    setCreating(true)
    setError(null)
    try {
      const existing = await productsApi.list({ sku, status: 'ACTIVE' })
      if (existing.items.length > 0) {
        throw new ApiError(
          'PRODUCT_DUPLICATE_SKU',
          'Ya existe un producto o servicio con ese SKU.',
          409,
        )
      }
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
      resetQuickForm()
      onSelect(product)
    } catch (e) {
      setError(toApiError(e))
    } finally {
      setCreating(false)
    }
  }

  return (
    <PickerModal
      visible={visible}
      onClose={close}
      title="Producto o servicio"
      searchPlaceholder="SKU, nombre o descripción"
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
      headerActions={
        <Button
          variant="primary"
          size="md"
          onPress={() => {
            setError(null)
            setShowQuickCreate((current) => !current)
          }}
        >
          {showQuickCreate ? 'Ocultar' : 'Añadir'}
        </Button>
      }
      error={error}
      results={results}
      keyExtractor={(product) => product.id}
      maxDialogWidth={640}
      maxDialogHeightPct={92}
      listMaxHeight={220}
      emptyState={<EmptyResults searched={searched} />}
      renderItem={(product) => (
        <PickerResultRow onPress={() => onSelect(product)}>
          <ProductResult product={product} campaign={campaign} />
        </PickerResultRow>
      )}
      footer={
        showQuickCreate ? (
          <QuickCreateForm
            sku={quickSku}
            onSkuChange={setQuickSku}
            name={quickName}
            onNameChange={setQuickName}
            price={quickPrice}
            onPriceChange={setQuickPrice}
            iva={quickIva}
            onIvaChange={setQuickIva}
            creating={creating}
            onSubmit={createQuick}
          />
        ) : null
      }
    />
  )
}

function EmptyResults({ searched }: { searched: boolean }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.emptyState}>
      <Ionicons
        name={searched ? 'search-outline' : 'cube-outline'}
        size={28}
        color={semantic.text.tertiary}
      />
      <Text style={[styles.emptyTitle, { color: semantic.text.primary }]}>
        {searched ? 'Sin resultados' : 'Busca en tu catálogo'}
      </Text>
      <Text style={[styles.empty, { color: semantic.text.secondary }]}>
        {searched
          ? 'Intenta con otro SKU, nombre o descripción. También puedes añadir un producto nuevo.'
          : 'Escribe SKU, nombre o descripción y presiona Buscar. Si todavía no existe, usa Añadir.'}
      </Text>
    </View>
  )
}

function ProductResult({
  product,
  campaign,
}: {
  product: Product
  campaign: { active: boolean; percentage: string } | null
}) {
  const { semantic } = useTheme()
  const discount = resolvePickerDiscount(product, campaign)
  return (
    <>
      <Text style={[styles.resultName, { color: semantic.text.primary }]} numberOfLines={1}>
        {product.name}
      </Text>
      <Text style={[styles.resultMeta, { color: semantic.text.secondary }]} numberOfLines={1}>
        {product.sku} · IVA {product.iva_rate} · ${Number(product.unit_price).toFixed(2)}
      </Text>
      {discount ? (
        <Text style={[styles.discountMeta, { color: semantic.accent.default }]} numberOfLines={1}>
          {discount}
        </Text>
      ) : null}
    </>
  )
}

function QuickCreateForm({
  sku,
  onSkuChange,
  name,
  onNameChange,
  price,
  onPriceChange,
  iva,
  onIvaChange,
  creating,
  onSubmit,
}: {
  sku: string
  onSkuChange: (value: string) => void
  name: string
  onNameChange: (value: string) => void
  price: string
  onPriceChange: (value: string) => void
  iva: ProductIvaRate
  onIvaChange: (value: ProductIvaRate) => void
  creating: boolean
  onSubmit: () => void
}) {
  const { semantic } = useTheme()
  return (
    <View style={[styles.quickBox, { borderColor: semantic.border.default }]}>
      <Text style={[styles.quickTitle, { color: semantic.text.primary }]}>Creación rápida</Text>
      <View style={styles.quickGrid}>
        <View style={styles.quickCol}>
          <FormField
            label="SKU"
            placeholder="PROD-001"
            leftIcon="barcode-outline"
            value={sku}
            onChangeText={onSkuChange}
            required
          />
        </View>
        <View style={styles.quickWide}>
          <FormField
            label="Nombre"
            placeholder="Producto o servicio"
            leftIcon="cube-outline"
            value={name}
            onChangeText={onNameChange}
            required
          />
        </View>
        <View style={styles.quickCol}>
          <MoneyField
            label="Precio"
            placeholder="0.00"
            value={price}
            onChangeText={onPriceChange}
            required
          />
        </View>
      </View>
      <SegmentedControl
        value={iva}
        options={[
          { value: '15', label: 'IVA 15%' },
          { value: '5', label: 'IVA 5%' },
          { value: '0', label: 'IVA 0%' },
          { value: 'EXENTO', label: 'Exento' },
        ]}
        onChange={onIvaChange}
      />
      <Button
        variant="secondary"
        size="md"
        isLoading={creating}
        isDisabled={!sku.trim() || !name.trim() || Number(price) <= 0}
        onPress={onSubmit}
      >
        Crear y usar
      </Button>
    </View>
  )
}

function resolvePickerDiscount(
  product: Product,
  campaign: { active: boolean; percentage: string } | null,
): string | null {
  const productPct = Number(product.discount_percentage ?? 0)
  const campaignPct = campaign?.active ? Number(campaign.percentage) : 0
  const effectivePct = Math.max(
    Number.isFinite(productPct) ? productPct : 0,
    Number.isFinite(campaignPct) ? campaignPct : 0,
  )

  if (effectivePct <= 0) return null

  const source = productPct >= campaignPct ? 'catálogo' : 'campaña global'
  const amount = (Number(product.unit_price) * (effectivePct / 100)).toFixed(2)
  return `Descuento sugerido: ${effectivePct}% por ${source} · $${amount} por unidad`
}

const styles = StyleSheet.create({
  emptyState: { alignItems: 'center', gap: spacing[2], padding: spacing[5] },
  emptyTitle: { fontSize: typography.size.base, fontWeight: typography.weight.bold },
  empty: { fontSize: typography.size.sm, lineHeight: 20, textAlign: 'center' },
  resultName: { fontSize: typography.size.base, fontWeight: typography.weight.semibold },
  resultMeta: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.xs },
  discountMeta: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  quickBox: { borderRadius: radius.md, borderWidth: 1, gap: spacing[3], padding: spacing[3] },
  quickTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  quickCol: { flex: 1, minWidth: 140 },
  quickWide: { flex: 2, minWidth: 220 },
})
