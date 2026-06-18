import React from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { productsApi } from '../api'
import { ProductForm } from '../components/ProductForm'
import { formValuesToUpdateProductInput } from '../form'
import { useProduct } from '../hooks/useProduct'
import type { ProductFormValues } from '../types'

export function EditProductScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const { product, loading, error, refresh } = useProduct(id ?? null)

  const {
    submitting,
    error: actionError,
    submit,
  } = useFormSubmit(async (values: ProductFormValues) => {
    if (!product) return
    const updated = await productsApi.update(
      product.id,
      formValuesToUpdateProductInput(values),
      createIdempotencyKey('product_update'),
    )
    toast.success('Producto actualizado')
    router.replace(Routes.tenant.productDetail(updated.id) as Href)
  })

  if (loading) return <LoadingSpinner fullScreen label="Cargando producto..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Editar producto" canGoBack />
      {error || !product ? (
        <EmptyState
          icon="alert-circle-outline"
          title="No se pudo cargar el producto"
          description={error?.message ?? 'El producto no existe o no está disponible.'}
          action={{ label: 'Reintentar', onPress: refresh }}
        />
      ) : (
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <ProductForm
            mode="edit"
            product={product}
            onSubmit={submit}
            isLoading={submitting}
            apiError={actionError}
          />
        </ScrollView>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], paddingBottom: spacing[12] },
})
