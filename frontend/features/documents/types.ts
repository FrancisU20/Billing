import type { DocumentStatus } from './schemas'

export type {
  BuyerIdType,
  BuyerMode,
  CreditNoteFormLine,
  CreditNoteLineInput,
  Document,
  DocumentLine,
  DocumentsPage,
  DocumentsSummary,
  DocumentStatus,
  EmitCreditNoteFormValues,
  EmitCreditNoteInput,
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
  doc_type?: string
  serie?: string
  q?: string
  date_from?: string
  date_to?: string
}
