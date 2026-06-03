import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiClient } from "@/lib/api-client";
import type { Tenant, CreateTenantRequest } from "@codelabs-billing/shared";

const ESTADO_COLORS: Record<string, string> = {
  TRIAL: "bg-blue-100 text-blue-700",
  ACTIVE: "bg-green-100 text-green-700",
  PAYMENT_DUE: "bg-yellow-100 text-yellow-700",
  GRACE_PERIOD: "bg-orange-100 text-orange-700",
  SUSPENDED: "bg-red-100 text-red-700",
  CANCELLED: "bg-gray-100 text-gray-600",
};

export function TenantsPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateTenantRequest>({ ruc: "", razon_social: "", nombre_comercial: "", ambiente_sri: "PRUEBAS" });

  const { data: tenants = [], isLoading } = useQuery<Tenant[]>({
    queryKey: ["tenants"],
    queryFn: () => apiClient.get<Tenant[]>("/tenants").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: CreateTenantRequest) => apiClient.post<Tenant>("/tenants", data).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["tenants"] }); setShowForm(false); setForm({ ruc: "", razon_social: "", nombre_comercial: "", ambiente_sri: "PRUEBAS" }); },
  });

  if (isLoading) return <p className="text-muted-foreground text-sm">Cargando...</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tenants</h1>
        <button onClick={() => setShowForm(true)} className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">Nuevo tenant</button>
      </div>

      {showForm && (
        <div className="rounded-lg border border-border bg-card p-6 space-y-4">
          <h2 className="font-semibold">Nuevo tenant</h2>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="text-sm font-medium">RUC *</label><input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" maxLength={13} value={form.ruc} onChange={(e) => setForm({ ...form, ruc: e.target.value })} /></div>
            <div><label className="text-sm font-medium">Ambiente SRI</label><select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={form.ambiente_sri} onChange={(e) => setForm({ ...form, ambiente_sri: e.target.value as "PRUEBAS" | "PRODUCCION" })}><option value="PRUEBAS">PRUEBAS</option><option value="PRODUCCION">PRODUCCION</option></select></div>
            <div className="col-span-2"><label className="text-sm font-medium">Razón social *</label><input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={form.razon_social} onChange={(e) => setForm({ ...form, razon_social: e.target.value })} /></div>
          </div>
          <div className="flex gap-3 justify-end">
            <button onClick={() => setShowForm(false)} className="rounded-md px-4 py-2 text-sm border border-input hover:bg-muted">Cancelar</button>
            <button onClick={() => createMutation.mutate(form)} disabled={createMutation.isPending || !form.ruc || !form.razon_social} className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50">{createMutation.isPending ? "Creando..." : "Crear tenant"}</button>
          </div>
        </div>
      )}

      <div className="rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left font-medium">RUC</th>
              <th className="px-4 py-3 text-left font-medium">Razón social</th>
              <th className="px-4 py-3 text-left font-medium">Estado</th>
              <th className="px-4 py-3 text-left font-medium">Ambiente</th>
              <th className="px-4 py-3 text-right font-medium">Comp. mes</th>
              <th className="px-4 py-3 text-left font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((tenant) => (
              <tr key={tenant.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                <td className="px-4 py-3 font-mono text-xs">{tenant.ruc}</td>
                <td className="px-4 py-3">{tenant.razon_social}</td>
                <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ESTADO_COLORS[tenant.estado] ?? "bg-gray-100 text-gray-600"}`}>{tenant.estado}</span></td>
                <td className="px-4 py-3"><span className={`text-xs font-medium ${tenant.ambiente_sri === "PRODUCCION" ? "text-green-600" : "text-yellow-600"}`}>{tenant.ambiente_sri}</span></td>
                <td className="px-4 py-3 text-right tabular-nums">{tenant.comprobantes_mes_actual}</td>
                <td className="px-4 py-3"><Link to={`/tenants/${tenant.id}`} className="text-xs text-primary underline-offset-2 hover:underline">Ver</Link></td>
              </tr>
            ))}
            {!tenants.length && <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground text-sm">No hay tenants</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
