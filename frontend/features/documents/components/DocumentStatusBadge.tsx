import React from 'react'
import { Badge } from '@/components/ui/Badge'
import { DOCUMENT_STATUS_BADGE_VARIANT, DOCUMENT_STATUS_LABELS } from '../constants'
import type { DocumentStatus } from '../types'

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <Badge
      label={DOCUMENT_STATUS_LABELS[status]}
      variant={DOCUMENT_STATUS_BADGE_VARIANT[status]}
      size="sm"
    />
  )
}
