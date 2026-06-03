import { z } from "zod";

export const ivaConfigSchema = z.object({
  codigo_porcentaje: z.string(),
  tarifa: z.number(),
  descripcion: z.string(),
});

export type IvaConfig = z.infer<typeof ivaConfigSchema>;

export const sriCatalogItemSchema = z.object({
  codigo: z.string(),
  descripcion: z.string(),
});

export type SriCatalogItem = z.infer<typeof sriCatalogItemSchema>;

export const sriConfigSchema = z.object({
  iva_vigente: ivaConfigSchema,
  tarifas_disponibles: z.array(ivaConfigSchema),
  formas_pago: z.array(sriCatalogItemSchema),
  tipos_identificacion: z.array(sriCatalogItemSchema),
});

export type SriConfig = z.infer<typeof sriConfigSchema>;
