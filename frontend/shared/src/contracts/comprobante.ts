import { z } from "zod";
import { offsetListResponseSchema } from "./api";

export const tipoComprobanteValues = ["01", "03", "04", "05", "06", "07"] as const;
export const tipoComprobanteSchema = z.enum(tipoComprobanteValues);
export type TipoComprobante = z.infer<typeof tipoComprobanteSchema>;

export const estadoComprobanteValues = [
  "DRAFT",
  "PENDING_VALIDATION",
  "VALIDATION_FAILED",
  "QUEUED",
  "PROCESSING",
  "XML_GENERATED",
  "XML_SIGNED",
  "SENT_TO_SRI",
  "RECEIVED_BY_SRI",
  "RETURNED_BY_SRI",
  "PENDING_AUTHORIZATION",
  "AUTHORIZED",
  "NOT_AUTHORIZED",
  "PENDING_CANCELLATION",
  "CANCELLED",
  "EMAIL_PENDING",
  "EMAIL_SENT",
  "EMAIL_FAILED",
  "FAILED",
  "RETRY_PENDING",
  "MANUAL_REVIEW_REQUIRED",
] as const;

export const estadoComprobanteSchema = z.enum(estadoComprobanteValues);
export type EstadoComprobante = z.infer<typeof estadoComprobanteSchema>;

export const retryComprobanteTipoValues = [
  "REENVIAR_SRI",
  "RECONSULTAR_AUTORIZACION",
  "REENVIAR_EMAIL",
] as const;

export const retryComprobanteTipoSchema = z.enum(retryComprobanteTipoValues);
export type RetryComprobanteTipo = z.infer<typeof retryComprobanteTipoSchema>;

export const comprobanteSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  tipo: tipoComprobanteSchema,
  clave_acceso: z.string().nullable(),
  establecimiento: z.string(),
  punto_emision: z.string(),
  secuencial: z.string().nullable(),
  estado: estadoComprobanteSchema,
  idempotency_key: z.string().nullable(),
  external_reference: z.string().nullable(),
  numero_autorizacion: z.string().nullable(),
  retry_count: z.number().int().nonnegative(),
  error_detalle: z.string().nullable(),
});

export type Comprobante = z.infer<typeof comprobanteSchema>;

export const createComprobanteRequestSchema = z.object({
  tipo: tipoComprobanteSchema.default("01"),
  establecimiento: z.string(),
  punto_emision: z.string(),
  datos: z.record(z.unknown()),
  idempotency_key: z.string().optional(),
  external_reference: z.string().nullable().optional(),
});

export type CreateComprobanteRequest = z.input<typeof createComprobanteRequestSchema>;

export const retryComprobanteRequestSchema = z.object({
  tipo: retryComprobanteTipoSchema,
});

export type RetryComprobanteRequest = z.input<typeof retryComprobanteRequestSchema>;

export const comprobanteListResponseSchema = offsetListResponseSchema(comprobanteSchema);
export type ComprobanteListResponse = z.infer<typeof comprobanteListResponseSchema>;
