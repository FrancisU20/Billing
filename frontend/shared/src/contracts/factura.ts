import { z } from "zod";

export const codigoImpuestoValues = ["2", "3", "5"] as const;
export const codigoImpuestoSchema = z.enum(codigoImpuestoValues);
export type CodigoImpuesto = z.infer<typeof codigoImpuestoSchema>;

export const tipoIdentificacionCompradorValues = ["04", "05", "06", "07", "08"] as const;
export const tipoIdentificacionCompradorSchema = z.enum(tipoIdentificacionCompradorValues);
export type TipoIdentificacionComprador = z.infer<typeof tipoIdentificacionCompradorSchema>;

export const obligadoContabilidadValues = ["SI", "NO"] as const;
export const obligadoContabilidadSchema = z.enum(obligadoContabilidadValues);
export type ObligadoContabilidad = z.infer<typeof obligadoContabilidadSchema>;

export const impuestoDetalleFacturaSchema = z.object({
  codigo: codigoImpuestoSchema,
  codigo_porcentaje: z.string(),
  tarifa: z.number(),
  base_imponible: z.number(),
  valor: z.number(),
});

export type ImpuestoDetalleFactura = z.input<typeof impuestoDetalleFacturaSchema>;

export const detalleFacturaSchema = z.object({
  codigo_principal: z.string(),
  descripcion: z.string(),
  cantidad: z.number(),
  precio_unitario: z.number(),
  descuento: z.number().default(0),
  precio_total_sin_impuesto: z.number(),
  impuestos: z.array(impuestoDetalleFacturaSchema).min(1),
  codigo_auxiliar: z.string().nullable().optional(),
});

export type DetalleFactura = z.input<typeof detalleFacturaSchema>;

export const pagoFacturaSchema = z.object({
  forma_pago: z.string(),
  total: z.number(),
  plazo: z.number().int().default(0),
  unidad_tiempo: z.string().default("dias"),
});

export type PagoFactura = z.input<typeof pagoFacturaSchema>;

export const datosFacturaSchema = z.object({
  tipo_identificacion_comprador: tipoIdentificacionCompradorSchema,
  identificacion_comprador: z.string(),
  razon_social_comprador: z.string(),
  email_comprador: z.string().email().nullable().optional(),
  direccion_comprador: z.string().nullable().optional(),
  fecha_emision: z.string(),
  obligado_contabilidad: obligadoContabilidadSchema.default("NO"),
  contribuyente_especial: z.string().nullable().optional(),
  direccion_establecimiento: z.string().default(""),
  detalles: z.array(detalleFacturaSchema).min(1),
  total_sin_impuestos: z.number(),
  total_descuento: z.number().default(0),
  importe_total: z.number(),
  propina: z.number().default(0),
  moneda: z.string().default("DOLAR"),
  pagos: z.array(pagoFacturaSchema).min(1),
  info_adicional: z.record(z.string()).nullable().optional(),
});

export type DatosFactura = z.input<typeof datosFacturaSchema>;
