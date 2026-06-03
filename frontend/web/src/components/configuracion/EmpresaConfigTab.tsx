"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { Tenant } from "@codelabs-billing/shared";

export function EmpresaConfigTab() {
  const { user } = useAuth();
  const tenantId = user?.tenantId ?? "";
  const queryClient = useQueryClient();

  const { data: tenant } = useQuery<Tenant>({
    queryKey: ["tenant", tenantId],
    queryFn: () => apiClient.get<Tenant>(`/tenants/${tenantId}`).then((r) => r.data),
    enabled: !!tenantId,
  });

  const [form, setForm] = useState({
    razon_social: "",
    nombre_comercial: "",
    ambiente_sri: "PRUEBAS" as "PRUEBAS" | "PRODUCCION",
  });

  useEffect(() => {
    if (tenant) {
      setForm({
        razon_social: tenant.razon_social,
        nombre_comercial: tenant.nombre_comercial ?? "",
        ambiente_sri: tenant.ambiente_sri,
      });
    }
  }, [tenant]);

  const updateMutation = useMutation({
    mutationFn: (data: typeof form) =>
      apiClient.patch(`/tenants/${tenantId}`, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant", tenantId] });
    },
  });

  if (!tenant) return <p className="text-sm text-muted-foreground">Cargando...</p>;

  return (
    <div className="max-w-lg space-y-4">
      <div>
        <label className="text-sm font-medium">RUC</label>
        <input
          className="mt-1 w-full rounded border border-input bg-muted px-3 py-2 text-sm text-muted-foreground"
          value={tenant.ruc}
          disabled
        />
        <p className="mt-1 text-xs text-muted-foreground">El RUC no puede modificarse.</p>
      </div>

      <div>
        <label className="text-sm font-medium">Razón social</label>
        <input
          className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm"
          value={form.razon_social}
          onChange={(e) => setForm({ ...form, razon_social: e.target.value })}
        />
      </div>

      <div>
        <label className="text-sm font-medium">Nombre comercial</label>
        <input
          className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm"
          placeholder="Nombre que aparece en los comprobantes"
          value={form.nombre_comercial}
          onChange={(e) => setForm({ ...form, nombre_comercial: e.target.value })}
        />
      </div>

      <div>
        <label className="text-sm font-medium">Ambiente SRI</label>
        <select
          className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm"
          value={form.ambiente_sri}
          onChange={(e) => setForm({ ...form, ambiente_sri: e.target.value as "PRUEBAS" | "PRODUCCION" })}
        >
          <option value="PRUEBAS">PRUEBAS</option>
          <option value="PRODUCCION">PRODUCCION</option>
        </select>
        {form.ambiente_sri === "PRODUCCION" && (
          <p className="mt-1 text-xs text-orange-600">
            Atención: en modo PRODUCCION los comprobantes tienen validez tributaria real.
          </p>
        )}
      </div>

      <button
        onClick={() => updateMutation.mutate(form)}
        disabled={updateMutation.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
      >
        {updateMutation.isPending ? "Guardando..." : "Guardar cambios"}
      </button>

      {updateMutation.isSuccess && (
        <p className="text-sm text-green-600">Cambios guardados correctamente.</p>
      )}
    </div>
  );
}
