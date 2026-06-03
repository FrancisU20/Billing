import { z } from "zod";

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
  estado: z.string(),
});

export type Establecimiento = z.infer<typeof establecimientoSchema>;

export const puntoEmisionSchema = z.object({
  id: z.string().uuid(),
  establecimiento_id: z.string().uuid(),
  codigo: z.string(),
  estado: z.string(),
});

export type PuntoEmision = z.infer<typeof puntoEmisionSchema>;
