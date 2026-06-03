import { z } from "zod";

export const estadoCertificateValues = ["ACTIVE", "EXPIRED", "REVOKED"] as const;
export const estadoCertificateSchema = z.enum(estadoCertificateValues);
export type EstadoCertificate = z.infer<typeof estadoCertificateSchema>;

export const uploadCertificateUrlResponseSchema = z.object({
  upload_url: z.string().url(),
  cert_id: z.string().uuid(),
  expires_in_seconds: z.number().int().positive(),
});

export type UploadCertificateUrlResponse = z.infer<typeof uploadCertificateUrlResponseSchema>;

export const confirmCertificateRequestSchema = z.object({
  cert_id: z.string().uuid(),
  s3_key_upload: z.string(),
  password: z.string(),
  nombre: z.string().nullable().optional(),
});

export type ConfirmCertificateRequest = z.input<typeof confirmCertificateRequestSchema>;

export const certificateSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  nombre: z.string().nullable(),
  fecha_emision: z.string().nullable(),
  fecha_expiracion: z.string().nullable(),
  estado: estadoCertificateSchema,
});

export type Certificate = z.infer<typeof certificateSchema>;
