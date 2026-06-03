import type { EstadoComprobante, EstadoTenant } from "@codelabs-billing/shared";

export type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger" | "accent";

export const comprobanteEstadoTone: Record<EstadoComprobante, BadgeTone> = {
  DRAFT: "neutral",
  PENDING_VALIDATION: "info",
  VALIDATION_FAILED: "danger",
  QUEUED: "warning",
  PROCESSING: "warning",
  XML_GENERATED: "info",
  XML_SIGNED: "info",
  SENT_TO_SRI: "accent",
  RECEIVED_BY_SRI: "accent",
  RETURNED_BY_SRI: "warning",
  PENDING_AUTHORIZATION: "accent",
  AUTHORIZED: "success",
  NOT_AUTHORIZED: "danger",
  PENDING_CANCELLATION: "warning",
  CANCELLED: "neutral",
  EMAIL_PENDING: "info",
  EMAIL_SENT: "success",
  EMAIL_FAILED: "warning",
  FAILED: "danger",
  RETRY_PENDING: "warning",
  MANUAL_REVIEW_REQUIRED: "danger",
};

export const tenantEstadoTone: Record<EstadoTenant, BadgeTone> = {
  TRIAL: "info",
  ACTIVE: "success",
  PAYMENT_DUE: "warning",
  GRACE_PERIOD: "warning",
  SUSPENDED: "danger",
  CANCELLED: "neutral",
};

export function certificateTone(estado: string): BadgeTone {
  if (estado === "ACTIVE") return "success";
  if (estado === "EXPIRED") return "danger";
  return "neutral";
}
