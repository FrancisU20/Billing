import { Badge } from '@/components/ui/Badge'
import { productStatusLabel } from '../constants'
import type { ProductStatus } from '../types'

export function ProductStatusBadge({ status }: { status: ProductStatus }) {
  return (
    <Badge
      label={productStatusLabel(status)}
      variant={status === 'ACTIVE' ? 'success' : 'neutral'}
      size="sm"
    />
  )
}
