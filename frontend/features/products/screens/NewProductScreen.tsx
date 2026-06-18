import React from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { productsApi } from '../api'
import { ProductForm } from '../components/ProductForm'
import { formValuesToCreateProductInput } from '../form'
import type { ProductFormValues } from '../types'

export function NewProductScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()

  const { submitting, error, submit } = useFormSubmit(async (values: ProductFormValues) => {
    const product = await productsApi.create(
      formValuesToCreateProductInput(values),
      createIdempotencyKey('product_create'),
    )
    toast.success('Producto creado')
    router.replace(Routes.tenant.productDetail(product.id) as Href)
  })

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Nuevo producto" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <ProductForm mode="create" onSubmit={submit} isLoading={submitting} apiError={error} />
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], paddingBottom: spacing[12] },
})
