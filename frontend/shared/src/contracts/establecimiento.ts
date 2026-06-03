import { z } from "zod";

export const estadoEstablecimientoValues = ["ACTIVE", "INACTIVE"] as const;
export const estadoEstablecimientoSchema = z.enum(estadoEstablecimientoValues);
export type EstadoEstablecimiento = z.infer<typeof estadoEstablecimientoSchema>;

export const createEstablecimientoRequestSchema = z.object({
  codigo: z.string(),
  direccion: z.string().nullable().optional(),
});

export type CreateEstablecimientoRequest = z.input<typeof createEstablecimientoRequestSchema>;

export const createPuntoEmisionRequestSchema = z.object({
  codigo: z.string(),
});

export type CreatePuntoEmisionRequest = z.input<typeof createPuntoEmisionRequestSchema>;

export const establecimientoSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  codigo: z.string(),
  direccion: z.string().nullable(),
  estado: estadoEstablecimientoSchema,
});

export type Establecimiento = z.infer<typeof establecimientoSchema>;

export const puntoEmisionSchema = z.object({
  id: z.string().uuid(),
  establecimiento_id: z.string().uuid(),
  codigo: z.string(),
  estado: estadoEstablecimientoSchema,
});

export type PuntoEmision = z.infer<typeof puntoEmisionSchema>;
