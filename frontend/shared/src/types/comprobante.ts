export type TipoComprobante = "01" | "03" | "04" | "05" | "06" | "07";

export type EstadoComprobante =
  | "DRAFT"
  | "PENDING_VALIDATION"
  | "VALIDATION_FAILED"
  | "QUEUED"
  | "PROCESSING"
  | "XML_GENERATED"
  | "XML_SIGNED"
  | "SENT_TO_SRI"
  | "RECEIVED_BY_SRI"
  | "RETURNED_BY_SRI"
  | "PENDING_AUTHORIZATION"
  | "AUTHORIZED"
  | "NOT_AUTHORIZED"
  | "PENDING_CANCELLATION"
  | "CANCELLED"
  | "EMAIL_PENDING"
  | "EMAIL_SENT"
  | "EMAIL_FAILED"
  | "FAILED"
  | "RETRY_PENDING"
  | "MANUAL_REVIEW_REQUIRED";

export interface Comprobante {
  id: string;
  tenant_id: string;
  tipo: TipoComprobante;
  clave_acceso: string | null;
  establecimiento: string;
  punto_emision: string;
  secuencial: string | null;
  estado: EstadoComprobante;
  idempotency_key: string | null;
  external_reference: string | null;
  numero_autorizacion: string | null;
  fecha_autorizacion: string | null;
  retry_count: number;
  error_detalle: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateComprobanteRequest {
  tipo: TipoComprobante;
  establecimiento: string;
  punto_emision: string;
  idempotency_key?: string;
  external_reference?: string;
  datos: Record<string, unknown>;
}

export interface ComprobanteListResponse {
  items: Comprobante[];
  total: number;
  page: number;
  page_size: number;
}
