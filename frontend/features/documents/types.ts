import type { DocumentStatus } from './schemas'

export type {
  BuyerIdType,
  BuyerMode,
  Document,
  DocumentLine,
  DocumentsPage,
  DocumentsSummary,
  DocumentStatus,
  EmitDocumentFormValues,
  EmitDocumentInput,
  EmitDocumentLineInput,
  EmitDocumentResult,
  IvaRate,
  PaymentMethod,
  SriErrorDetail,
} from './schemas'

export interface DocumentListFilters {
  status?: DocumentStatus
  serie?: string
  q?: string
  date_from?: string
  date_to?: string
}
