import React from 'react'
import { Badge } from '@/components/ui/Badge'
import { CLIENT_STATUS_LABELS } from '../constants'
import type { ClientStatus } from '../types'

export function ClientStatusBadge({ status }: { status: ClientStatus }) {
  return (
    <Badge
      label={CLIENT_STATUS_LABELS[status]}
      variant={status === 'active' ? 'success' : 'neutral'}
      size="sm"
    />
  )
}
