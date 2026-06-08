import React from 'react'
import { Badge } from '@/components/ui/Badge'
import { TENANT_STATUS_LABELS } from '../constants'
import type { TenantStatus } from '../types'

const statusMap: Record<TenantStatus, { label: string; variant: 'success' | 'error' | 'warning' }> =
  {
    active: { label: TENANT_STATUS_LABELS.active, variant: 'success' },
    suspended: { label: TENANT_STATUS_LABELS.suspended, variant: 'error' },
    inactive: { label: TENANT_STATUS_LABELS.inactive, variant: 'warning' },
  }

export function TenantStatusBadge({ status }: { status: TenantStatus }) {
  const { label, variant } = statusMap[status] ?? { label: status, variant: 'neutral' as const }
  return <Badge label={label} variant={variant} size="sm" />
}
