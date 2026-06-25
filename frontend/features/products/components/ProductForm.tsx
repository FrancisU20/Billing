import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { FormActions } from '@/components/ui/FormActions'
import { FormField } from '@/components/ui/FormField'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { MoneyField, PercentField } from '@/components/ui/SpecializedFields'
import type { ApiError } from '@/lib/api/errors'
import { useTheme } from '@/lib/theme-context'
import { spacing, typography } from '@/constants/tokens'
import { PRODUCT_KIND_OPTIONS, PRODUCT_STATUS_OPTIONS, PRODUCT_UNIT_OPTIONS } from '../constants'
import { defaultProductFormValues } from '../form'
import { productFormSchema } from '../schemas'
import { generateProductSku, SKU_PLACEHOLDER } from '../sku'
import type { Product, ProductFormValues } from '../types'
import { GenerateSkuButton } from './GenerateSkuButton'

interface ProductFormProps {
  mode: 'create' | 'edit'
  product?: Product
  onSubmit: (values: ProductFormValues) => void | Promise<void>
  isLoading?: boolean
  apiError?: ApiError | null
}

export function ProductForm({ mode, product, onSubmit, isLoading, apiError }: ProductFormProps) {
  const { semantic } = useTheme()
  const {
    control,
    handleSubmit,
    setValue,
    formState: { errors, isValid },
  } = useForm<ProductFormValues>({
    resolver: zodResolver(productFormSchema),
    defaultValues: defaultProductFormValues(product),
    mode: 'onChange',
  })
  const stockEnabled = useWatch({ control, name: 'stock_enabled' })

  function handleGenerateSku() {
    setValue('sku', generateProductSku(), { shouldDirty: true, shouldValidate: true })
  }

  return (
    <View style={styles.container}>
      <View style={styles.grid}>
        <View style={styles.col}>
          <Controller
            control={control}
            name="sku"
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="SKU"
                placeholder={SKU_PLACEHOLDER}
                leftIcon="barcode-outline"
                error={errors.sku?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
                rightElement={<GenerateSkuButton onPress={handleGenerateSku} />}
                required
              />
            )}
          />
        </View>
        <View style={styles.colWide}>
          <Controller
            control={control}
            name="name"
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Nombre"
                placeholder="Producto o servicio"
                leftIcon="cube-outline"
                error={errors.name?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
                required
              />
            )}
          />
        </View>
      </View>

      <Controller
        control={control}
        name="description"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Descripción para factura"
            placeholder="Detalle que se enviará al SRI"
            leftIcon="document-text-outline"
            error={errors.description?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
          />
        )}
      />

      <FormBlock title="Tipo">
        <Controller
          control={control}
          name="kind"
          render={({ field: { onChange, value } }) => (
            <SegmentedControl
              value={value}
              options={PRODUCT_KIND_OPTIONS.map((option) => ({
                label: option.label,
                value: option.value,
              }))}
              onChange={(next) => onChange(next)}
            />
          )}
        />
      </FormBlock>

      <View style={styles.grid}>
        <View style={styles.col}>
          <Controller
            control={control}
            name="unit_price"
            render={({ field: { onChange, onBlur, value } }) => (
              <MoneyField
                label="Precio unitario"
                placeholder="0.00"
                error={errors.unit_price?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
                required
              />
            )}
          />
        </View>
        <View style={styles.col}>
          <Controller
            control={control}
            name="discount_percentage"
            render={({ field: { onChange, onBlur, value } }) => (
              <PercentField
                label="Descuento (%)"
                placeholder="0.00"
                error={errors.discount_percentage?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
              />
            )}
          />
        </View>
      </View>

      <FormBlock title="Unidad">
        <Controller
          control={control}
          name="unit"
          render={({ field: { onChange, value } }) => (
            <SegmentedControl
              stretch
              columns={6}
              value={value}
              options={PRODUCT_UNIT_OPTIONS}
              onChange={onChange}
            />
          )}
        />
      </FormBlock>

      <FormBlock title="IVA">
        <Controller
          control={control}
          name="iva_rate"
          render={({ field: { onChange, value } }) => (
            <SegmentedControl
              stretch
              columns={4}
              value={value}
              options={[
                { value: '15', label: '15%' },
                { value: '5', label: '5%' },
                { value: '0', label: '0%' },
                { value: 'EXENTO', label: 'Exento' },
              ]}
              onChange={onChange}
            />
          )}
        />
      </FormBlock>

      <FormBlock title="Stock">
        <Controller
          control={control}
          name="stock_enabled"
          render={({ field: { onChange, value } }) => (
            <SegmentedControl
              value={value ? 'yes' : 'no'}
              options={[
                { label: 'Sin stock', value: 'no' },
                { label: 'Controlar stock', value: 'yes' },
              ]}
              onChange={(next) => onChange(next === 'yes')}
            />
          )}
        />
        {stockEnabled ? (
          <View style={styles.grid}>
            <View style={styles.col}>
              <Controller
                control={control}
                name="stock_quantity"
                render={({ field: { onChange, onBlur, value } }) => (
                  <FormField
                    label="Stock actual"
                    placeholder="0"
                    keyboardType="decimal-pad"
                    leftIcon="layers-outline"
                    error={errors.stock_quantity?.message}
                    onChangeText={onChange}
                    onBlur={onBlur}
                    value={value}
                  />
                )}
              />
            </View>
            <View style={styles.col}>
              <Controller
                control={control}
                name="low_stock_threshold"
                render={({ field: { onChange, onBlur, value } }) => (
                  <FormField
                    label="Umbral bajo"
                    placeholder="0"
                    keyboardType="decimal-pad"
                    leftIcon="alert-circle-outline"
                    error={errors.low_stock_threshold?.message}
                    onChangeText={onChange}
                    onBlur={onBlur}
                    value={value}
                  />
                )}
              />
            </View>
          </View>
        ) : null}
      </FormBlock>

      {mode === 'edit' ? (
        <FormBlock title="Estado">
          <Controller
            control={control}
            name="status"
            render={({ field: { onChange, value } }) => (
              <SegmentedControl
                value={value}
                options={PRODUCT_STATUS_OPTIONS.map((option) => ({
                  label: option.label,
                  value: option.value,
                }))}
                onChange={(next) => onChange(next)}
              />
            )}
          />
        </FormBlock>
      ) : null}

      {apiError ? <ApiErrorBanner error={apiError} /> : null}

      <FormActions
        submitLabel={mode === 'create' ? 'Crear producto' : 'Guardar cambios'}
        isSubmitting={isLoading}
        isSubmitDisabled={!isValid}
        onSubmit={handleSubmit(onSubmit)}
      />

      <Text style={[styles.note, { color: semantic.text.tertiary }]}>
        El SKU es tu propio código — lo usamos solo para identificar el producto en tu catálogo.
        Para la factura generamos automáticamente el código corto que exige el SRI. Las facturas
        emitidas conservan su snapshot aunque luego edites el producto.
      </Text>
    </View>
  )
}

function FormBlock({ title, children }: { title: string; children: React.ReactNode }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.block}>
      <Text style={[styles.blockTitle, { color: semantic.text.primary }]}>{title}</Text>
      {children}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[4] },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  col: { flex: 1, minWidth: 180 },
  colWide: { flex: 2, minWidth: 260 },
  block: { gap: spacing[2] },
  blockTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  note: { fontSize: typography.size.xs, lineHeight: typography.size.xs * 1.5 },
})
