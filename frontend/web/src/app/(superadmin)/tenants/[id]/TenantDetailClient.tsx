"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { Tenant } from "@codelabs-billing/shared";

const ESTADOS = ["TRIAL", "ACTIVE", "PAYMENT_DUE", "GRACE_PERIOD", "SUSPENDED", "CANCELLED"];

export default function TenantDetailClient({ id }: { id: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: tenant, isLoading } = useQuery<Tenant>({
    queryKey: ["tenant", id],
    queryFn: () => apiClient.get<Tenant>(`/tenants/${id}`).then((r) => r.data),
  });

  const [form, setForm] = useState({
    razon_social: "",
    nombre_comercial: "",
    ambiente_sri: "PRUEBAS",
    estado: "TRIAL",
  });

  useEffect(() => {
    if (tenant) {
      setForm({
        razon_social: tenant.razon_social,
        nombre_comercial: tenant.nombre_comercial ?? "",
        ambiente_sri: tenant.ambiente_sri,
        estado: tenant.estado,
      });
    }
  }, [tenant]);

  const updateMutation = useMutation({
    mutationFn: (data: typeof form) =>
      apiClient.patch(`/tenants/${id}`, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenants"] });
      queryClient.invalidateQueries({ queryKey: ["tenant", id] });
    },
  });

  if (isLoading) return <p className="text-sm text-muted-foreground">Cargando...</p>;
  if (!tenant) return <p className="text-destructive text-sm">Tenant no encontrado</p>;

  return (
    <div className="max-w-lg space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="text-sm text-muted-foreground hover:text-foreground">
          ← Volver
        </button>
        <h1 className="text-xl font-bold">{tenant.ruc}</h1>
      </div>

      <div className="space-y-4 rounded-lg border border-border p-4">
        <div>
          <label className="text-sm font-medium">RUC</label>
          <input
            className="mt-1 w-full rounded border border-input bg-muted px-3 py-2 text-sm text-muted-foreground"
            value={tenant.ruc}
            disabled
          />
        </div>

        {(["razon_social", "nombre_comercial"] as const).map((k) => (
          <div key={k}>
            <label className="text-sm font-medium capitalize">{k.replace("_", " ")}</label>
            <input
              className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm"
              value={form[k]}
              onChange={(e) => setForm({ ...form, [k]: e.target.value })}
            />
          </div>
        ))}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm font-medium">Estado</label>
            <select
              className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm"
              value={form.estado}
              onChange={(e) => setForm({ ...form, estado: e.target.value })}
            >
              {ESTADOS.map((e) => <option key={e} value={e}>{e}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">Ambiente SRI</label>
            <select
              className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm"
              value={form.ambiente_sri}
              onChange={(e) => setForm({ ...form, ambiente_sri: e.target.value })}
            >
              <option value="PRUEBAS">PRUEBAS</option>
              <option value="PRODUCCION">PRODUCCION</option>
            </select>
          </div>
        </div>

        <button
          onClick={() => updateMutation.mutate(form)}
          disabled={updateMutation.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {updateMutation.isPending ? "Guardando..." : "Guardar cambios"}
        </button>
        {updateMutation.isSuccess && <p className="text-sm text-green-600">Cambios guardados.</p>}
      </div>

      <div className="rounded-lg border border-border p-4 space-y-2">
        <h2 className="text-sm font-semibold">Resumen</h2>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <span className="text-muted-foreground">Comprobantes este mes</span>
          <span className="font-mono">{tenant.comprobantes_mes_actual}</span>
        </div>
      </div>
    </div>
  );
}
