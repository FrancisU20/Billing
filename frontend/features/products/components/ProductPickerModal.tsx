import React, { useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { PickerModal, PickerResultRow } from '@/components/ui/PickerModal'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { MoneyField } from '@/components/ui/SpecializedFields'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { ApiError, toApiError } from '@/lib/api/errors'
import { usePickerSearchState } from '@/lib/hooks/usePickerSearchState'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { productsApi } from '../api'
import { resolvePickerDiscount } from '../discount'
import { generateProductSku, SKU_PLACEHOLDER } from '../sku'
import type { Product, ProductIvaRate } from '../types'
import { GenerateSkuButton } from './GenerateSkuButton'

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
  const [quickSku, setQuickSku] = useState('')
  const [quickName, setQuickName] = useState('')
  const [quickPrice, setQuickPrice] = useState('0.00')
  const [quickIva, setQuickIva] = useState<ProductIvaRate>('15')

  function resetQuickForm() {
    setQuickSku('')
    setQuickName('')
    setQuickPrice('0.00')
    setQuickIva('15')
  }

  const {
    query,
    setQuery,
    results,
    searched,
    loading,
    creating,
    setCreating,
    error,
    setError,
    showQuickCreate,
    setShowQuickCreate,
    search,
    close,
  } = usePickerSearchState<Product>(
    visible,
    onClose,
    (q) => productsApi.list({ q, status: 'ACTIVE' }),
    resetQuickForm,
  )

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
            onGenerateSku={() => setQuickSku(generateProductSku())}
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
        {product.sku} · IVA {product.iva_rate} · {product.unit_price}
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
  onGenerateSku,
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
  onGenerateSku: () => void
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
            placeholder={SKU_PLACEHOLDER}
            leftIcon="barcode-outline"
            value={sku}
            onChangeText={onSkuChange}
            rightElement={<GenerateSkuButton onPress={onGenerateSku} />}
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
  quickCol: { flex: 1, minWidth: 180 },
  quickWide: { flex: 2, minWidth: 240 },
})
