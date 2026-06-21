import { formatCurrency } from '@/lib/utils/format'
import { UNLIMITED_LIMIT } from './constants'
import type { LimitCycle, Plan } from './types'

export function isUnlimitedLimit(value: number): boolean {
  return value === UNLIMITED_LIMIT
}

export function formatPlanLimit(value: number, singular: string, plural: string): string {
  if (isUnlimitedLimit(value)) return 'Ilimitado'
  return `${value.toLocaleString('es-EC')} ${value === 1 ? singular : plural}`
}

export function formatDocumentLimit(plan: Pick<Plan, 'document_limit' | 'limit_cycle'>): string {
  if (isUnlimitedLimit(plan.document_limit)) return 'Docs ilimitados'
  return `${plan.document_limit.toLocaleString('es-EC')} docs/${cycleSuffix(plan.limit_cycle)}`
}

export function formatBillingPrice(
  plan: Pick<Plan, 'monthly_price' | 'annual_price'>,
  billingCycle: LimitCycle = 'month',
): string {
  const price = billingCycle === 'year' ? plan.annual_price : plan.monthly_price
  return `${formatCurrency(price)} / ${cycleSuffix(billingCycle)}`
}

export function isCustomQuotePlan(plan: Pick<Plan, 'self_service'>): boolean {
  return !plan.self_service
}

export function cycleLabel(cycle: LimitCycle): string {
  return cycle === 'month' ? 'Mensual' : 'Anual'
}

function cycleSuffix(cycle: LimitCycle): string {
  return cycle === 'month' ? 'mes' : 'año'
}
