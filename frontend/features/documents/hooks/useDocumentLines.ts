import { useEffect, useRef, useState } from 'react'
import { useFieldArray, useWatch } from 'react-hook-form'
import type { Control, UseFormGetValues, UseFormSetValue } from 'react-hook-form'
import type { Product } from '@/features/products/types'
import {
  resolveDiscountPolicy,
  resolveSuggestedDiscount,
  shouldAutoApplySuggestedDiscount,
} from '../form'
import type { EmitDocumentFormValues } from '../schemas'

type Campaign = { active: boolean; percentage: string } | null

function reindexByRemovedLine<T>(
  values: Record<number, T>,
  removedIndex: number,
): Record<number, T> {
  return Object.entries(values).reduce<Record<number, T>>((next, [key, value]) => {
    const index = Number(key)
    if (index < removedIndex) {
      next[index] = value
    } else if (index > removedIndex) {
      next[index - 1] = value
    }
    return next
  }, {})
}

function computeDiscountPreview(
  lines: EmitDocumentFormValues['lines'],
  productDiscountByLine: Record<number, string | null>,
  campaign: Campaign,
): { discountedLines: number; suggestedDiscount: number } {
  return lines.reduce(
    (acc, line, index) => {
      const policy = resolveDiscountPolicy(
        line.quantity,
        line.unit_price,
        productDiscountByLine[index] ?? null,
        campaign,
      )
      const amount = Number(policy.amount)
      if (policy.source !== 'none' && Number.isFinite(amount) && amount > 0) {
        acc.discountedLines += 1
        acc.suggestedDiscount += amount
      }
      return acc
    },
    { discountedLines: 0, suggestedDiscount: 0 },
  )
}

export function useDocumentLines(
  control: Control<EmitDocumentFormValues>,
  getValues: UseFormGetValues<EmitDocumentFormValues>,
  setValue: UseFormSetValue<EmitDocumentFormValues>,
  campaign: Campaign,
) {
  const { fields, append, remove } = useFieldArray({ control, name: 'lines' })
  const lines = useWatch({ control, name: 'lines' })
  const [productDiscountByLine, setProductDiscountByLine] = useState<Record<number, string | null>>(
    {},
  )
  const lastSuggestedDiscountByLine = useRef<Record<number, string>>({})

  // Auto-sync suggested discounts when campaign or line values change.
  // Only applies if the current discount is still tracking the previous suggestion
  // (i.e. the user hasn't manually overridden it yet).
  useEffect(() => {
    for (const [index, line] of (lines ?? []).entries()) {
      const suggested = resolveSuggestedDiscount(
        line.quantity,
        line.unit_price,
        productDiscountByLine[index] ?? null,
        campaign,
      )
      if (
        shouldAutoApplySuggestedDiscount(
          line.discount,
          lastSuggestedDiscountByLine.current[index],
          suggested,
        )
      ) {
        setValue(`lines.${index}.discount`, suggested, { shouldDirty: true, shouldValidate: true })
      }
      lastSuggestedDiscountByLine.current[index] = suggested
    }
  }, [campaign, lines, productDiscountByLine, setValue])

  function addProductLine(product: Product) {
    const existingIndex = (lines ?? []).findIndex((line) => line.product_id === product.id)
    if (existingIndex >= 0) {
      const current = Number(getValues(`lines.${existingIndex}.quantity`)) || 0
      setValue(`lines.${existingIndex}.quantity`, String(current + 1), {
        shouldDirty: true,
        shouldValidate: true,
      })
      return
    }

    const newIndex = fields.length
    const suggested = resolveSuggestedDiscount(
      '1',
      product.unit_price,
      product.discount_percentage,
      campaign,
    )
    append({
      product_id: product.id,
      code: product.invoice_code,
      description: product.description || product.name,
      quantity: '1',
      unit_price: product.unit_price,
      discount: suggested,
      iva_rate: product.iva_rate,
    })
    setProductDiscountByLine((current) => ({ ...current, [newIndex]: product.discount_percentage }))
    lastSuggestedDiscountByLine.current[newIndex] = suggested
  }

  function removeLine(index: number) {
    remove(index)
    setProductDiscountByLine((current) => reindexByRemovedLine(current, index))
    lastSuggestedDiscountByLine.current = reindexByRemovedLine(
      lastSuggestedDiscountByLine.current,
      index,
    )
  }

  const discountPreview = computeDiscountPreview(lines ?? [], productDiscountByLine, campaign)

  return { fields, lines, productDiscountByLine, discountPreview, addProductLine, removeLine }
}
