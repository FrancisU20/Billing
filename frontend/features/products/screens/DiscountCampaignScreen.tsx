import React, { useEffect, useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { PercentField } from '@/components/ui/SpecializedFields'
import { isPercentageInput } from '@/lib/utils/form-validators'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { productsApi } from '../api'
import { useDiscountCampaign } from '../hooks/useDiscountCampaign'
import { updateDiscountCampaignSchema } from '../schemas'

export function DiscountCampaignScreen() {
  const toast = useToast()
  const { semantic } = useTheme()
  const { campaign, loading, error, refresh } = useDiscountCampaign()

  const [active, setActive] = useState(false)
  const [percentage, setPercentage] = useState('0.00')
  const percentageError = isPercentageInput(percentage) ? undefined : 'Debe estar entre 0 y 100'

  useRefreshOnFocus(refresh)

  useEffect(() => {
    if (!campaign) return
    setActive(campaign.active)
    setPercentage(campaign.percentage)
  }, [campaign])

  const {
    submitting,
    error: submitError,
    submit,
  } = useFormSubmit(async () => {
    const payload = updateDiscountCampaignSchema.parse({
      active,
      percentage: percentage.trim(),
    })
    await productsApi.updateDiscountCampaign(
      payload,
      createIdempotencyKey('discount_campaign_update'),
    )
    toast.success(active ? 'Campaña activada' : 'Campaña desactivada')
    await refresh()
  })

  if (loading) return <LoadingSpinner fullScreen label="Cargando campaña..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar
        title="Descuento global"
        subtitle="Aplica a toda la mercadería del catálogo"
        canGoBack
      />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {error ? <ApiErrorBanner error={error} /> : null}

        <View
          style={[
            styles.card,
            { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
          ]}
        >
          <Text style={[styles.label, { color: semantic.text.secondary }]}>Estado</Text>
          <SegmentedControl
            value={active ? 'active' : 'inactive'}
            options={[
              { label: 'Desactivada', value: 'inactive' },
              { label: 'Activa', value: 'active' },
            ]}
            onChange={(next) => setActive(next === 'active')}
          />

          <PercentField
            label="Porcentaje de descuento (%)"
            placeholder="0.00"
            error={percentageError}
            onChangeText={setPercentage}
            value={percentage}
          />

          {submitError ? <ApiErrorBanner error={submitError} /> : null}

          <Button
            variant="primary"
            size="lg"
            fullWidth
            isLoading={submitting}
            isDisabled={!!percentageError}
            onPress={submit}
          >
            Guardar
          </Button>

          <Text style={[styles.note, { color: semantic.text.tertiary }]}>
            Cuando está activa, el facturador sugiere este % en cada línea, salvo que el descuento
            propio del producto sea mayor — en ese caso se prioriza el del producto.
          </Text>
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
  card: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[3],
    padding: spacing[4],
  },
  label: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  note: { fontSize: typography.size.xs, lineHeight: typography.size.xs * 1.5 },
})
