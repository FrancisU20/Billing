// v2026.06.04c
import { z } from "zod";

export const ambienteSriValues = ["PRUEBAS", "PRODUCCION"] as const;
export const ambienteSriSchema = z.enum(ambienteSriValues);
export type AmbienteSri = z.infer<typeof ambienteSriSchema>;

export const estadoTenantValues = [
  "TRIAL",
  "ACTIVE",
  "PAYMENT_DUE",
  "GRACE_PERIOD",
  "SUSPENDED",
  "CANCELLED",
] as const;

export const estadoTenantSchema = z.enum(estadoTenantValues);
export type EstadoTenant = z.infer<typeof estadoTenantSchema>;

export const tenantSchema = z.object({
  id: z.string().uuid(),
  ruc: z.string().regex(/^\d{13}$/),
  razon_social: z.string(),
  nombre_comercial: z.string().nullable(),
  estado: estadoTenantSchema,
  ambiente_sri: ambienteSriSchema,
  comprobantes_mes_actual: z.number().int().nonnegative(),
});

export type Tenant = z.infer<typeof tenantSchema>;

export const createTenantRequestSchema = z.object({
  ruc: z.string().regex(/^\d{13}$/),
  razon_social: z.string().min(1),
  admin_email: z.string().email("Correo electrónico inválido"),
  nombre_comercial: z.string().nullable().optional(),
  ambiente_sri: ambienteSriSchema.default("PRUEBAS").optional(),
});

export type CreateTenantRequest = z.input<typeof createTenantRequestSchema>;

export const updateTenantRequestSchema = z.object({
  razon_social: z.string().min(1).nullable().optional(),
  nombre_comercial: z.string().nullable().optional(),
  ambiente_sri: ambienteSriSchema.nullable().optional(),
  estado: estadoTenantSchema.nullable().optional(),
});

export type UpdateTenantRequest = z.input<typeof updateTenantRequestSchema>;
