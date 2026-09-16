import { formatCurrency } from '@/lib/utils/format'
import type { Product } from './types'

/** Computes the effective discount label for a product in a picker context,
 * applying the same ceiling rule as the backend: max(product%, campaign%). */
export function resolvePickerDiscount(
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
  const amount = Number(product.unit_price) * (effectivePct / 100)
  return `Descuento sugerido: ${effectivePct}% por ${source} · ${formatCurrency(amount)} por unidad`
}
