import type { DocumentStatus } from './schemas'

export type {
  BuyerIdType,
  BuyerMode,
  Document,
  DocumentLine,
  DocumentsPage,
  DocumentStatus,
  EmitDocumentFormValues,
  EmitDocumentInput,
  EmitDocumentLineInput,
  IvaRate,
  PaymentMethod,
  SriErrorDetail,
} from './schemas'

export interface DocumentListFilters {
  status?: DocumentStatus
  serie?: string
  date_from?: string
  date_to?: string
}
