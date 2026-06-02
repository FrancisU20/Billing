export type EstadoTenant =
  | "TRIAL"
  | "ACTIVE"
  | "PAYMENT_DUE"
  | "GRACE_PERIOD"
  | "SUSPENDED"
  | "CANCELLED";

export interface Tenant {
  id: string;
  ruc: string;
  razon_social: string;
  nombre_comercial: string | null;
  estado: EstadoTenant;
  ambiente_sri: "PRUEBAS" | "PRODUCCION";
  plan_id: string | null;
  comprobantes_mes_actual: number;
  created_at: string;
  updated_at: string;
}

export interface CreateTenantRequest {
  ruc: string;
  razon_social: string;
  nombre_comercial?: string;
  ambiente_sri?: "PRUEBAS" | "PRODUCCION";
}
