"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { getApiErrorMessage } from "@/lib/api-errors";
import { hasErrors, required, type FieldErrors } from "@/lib/validation";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field, Input, Select } from "@/components/ui/Form";
import { LoadingState } from "@/components/ui/LoadingState";
import { useToast } from "@/components/ui/Toast";
import type { AmbienteSri, Tenant, UpdateTenantRequest } from "@codelabs-billing/shared";

type EmpresaForm = {
  razon_social: string;
  nombre_comercial: string;
  ambiente_sri: AmbienteSri;
};

type EmpresaField = "razon_social";

export function EmpresaConfigTab() {
  const { user } = useAuth();
  const tenantId = user?.tenantId ?? "";
  const queryClient = useQueryClient();
  const toast = useToast();
  const [errors, setErrors] = useState<FieldErrors<EmpresaField>>({});

  const { data: tenant, isLoading } = useQuery<Tenant>({
    queryKey: ["tenant", tenantId],
    queryFn: () => apiClient.get<Tenant>(`/tenants/${tenantId}`).then((r) => r.data),
    enabled: !!tenantId,
  });

  const [form, setForm] = useState<EmpresaForm>({
    razon_social: "",
    nombre_comercial: "",
    ambiente_sri: "PRUEBAS",
  });

  useEffect(() => {
    if (!tenant) return;
    setForm({
      razon_social: tenant.razon_social,
      nombre_comercial: tenant.nombre_comercial ?? "",
      ambiente_sri: tenant.ambiente_sri,
    });
  }, [tenant]);

  const updateMutation = useMutation({
    mutationFn: (data: UpdateTenantRequest) => apiClient.patch(`/tenants/${tenantId}`, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant", tenantId] });
      toast.success("Datos de empresa actualizados");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "No se pudo guardar la empresa")),
  });

  const submit = () => {
    const nextErrors = { razon_social: required(form.razon_social, "Razón social") };
    setErrors(nextErrors);
    if (hasErrors(nextErrors)) return;
    updateMutation.mutate(form);
  };

  if (isLoading) return <LoadingState />;
  if (!tenant) return <p className="text-sm text-muted-foreground">No se encontró la empresa.</p>;

  return (
    <div className="max-w-lg space-y-4">
      <Field label="RUC" hint="El RUC no puede modificarse.">
        <Input value={tenant.ruc} disabled />
      </Field>

      <Field label="Razón social" error={errors.razon_social}>
        <Input
          value={form.razon_social}
          hasError={!!errors.razon_social}
          onChange={(event) => setForm({ ...form, razon_social: event.target.value })}
        />
      </Field>

      <Field label="Nombre comercial">
        <Input
          placeholder="Nombre que aparece en los comprobantes"
          value={form.nombre_comercial}
          onChange={(event) => setForm({ ...form, nombre_comercial: event.target.value })}
        />
      </Field>

      <Field label="Ambiente SRI">
        <Select value={form.ambiente_sri} onChange={(event) => setForm({ ...form, ambiente_sri: event.target.value as AmbienteSri })}>
          <option value="PRUEBAS">PRUEBAS</option>
          <option value="PRODUCCION">PRODUCCION</option>
        </Select>
      </Field>

      {form.ambiente_sri === "PRODUCCION" && (
        <Alert tone="warning">Atención: en modo PRODUCCION los comprobantes tienen validez tributaria real.</Alert>
      )}

      <Button onClick={submit} isLoading={updateMutation.isPending}>
        Guardar cambios
      </Button>
    </div>
  );
}
