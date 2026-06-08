import React from 'react'
import { Badge } from '@/components/ui/Badge'
import type { TenantStatus } from '../types'

const statusMap: Record<TenantStatus, { label: string; variant: 'success' | 'error' | 'warning' }> = {
  active: { label: 'Activo', variant: 'success' },
  suspended: { label: 'Suspendido', variant: 'error' },
  pending: { label: 'Pendiente', variant: 'warning' },
}

export function TenantStatusBadge({ status }: { status: TenantStatus }) {
  const { label, variant } = statusMap[status] ?? { label: status, variant: 'neutral' as const }
  return <Badge label={label} variant={variant} size="sm" />
}
