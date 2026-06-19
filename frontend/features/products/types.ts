export type {
  CreateProductInput,
  DiscountCampaign,
  Product,
  ProductFormValues,
  ProductIvaRate,
  ProductKind,
  ProductsPage,
  ProductStatus,
  UpdateDiscountCampaignInput,
  UpdateProductInput,
} from './schemas'
import type { ProductKind, ProductStatus } from './schemas'

export interface ProductListFilters {
  q?: string
  sku?: string
  kind?: ProductKind
  status?: ProductStatus
}
