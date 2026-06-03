import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { apiClient } from "@/lib/api-client";
import { getApiErrorMessage } from "@/lib/api-errors";
import { tenantEstadoTone } from "@/lib/status-styles";
import { hasErrors, required, type FieldErrors } from "@/lib/validation";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Field, Input, Select } from "@/components/ui/Form";
import { LoadingState } from "@/components/ui/LoadingState";
import { useToast } from "@/components/ui/Toast";
import type { AmbienteSri, EstadoTenant, Tenant, UpdateTenantRequest } from "@codelabs-billing/shared";

type TenantUpdateForm = {
  razon_social: string;
  nombre_comercial: string;
  ambiente_sri: AmbienteSri;
  estado: EstadoTenant;
};

type TenantUpdateField = "razon_social";

const ESTADOS: EstadoTenant[] = ["TRIAL", "ACTIVE", "PAYMENT_DUE", "GRACE_PERIOD", "SUSPENDED", "CANCELLED"];

function validateForm(form: TenantUpdateForm): FieldErrors<TenantUpdateField> {
  return { razon_social: required(form.razon_social, "Razón social") };
}

export function TenantDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [errors, setErrors] = useState<FieldErrors<TenantUpdateField>>({});

  const { data: tenant, isLoading } = useQuery<Tenant>({
    queryKey: ["tenant", id],
    queryFn: () => apiClient.get<Tenant>(`/tenants/${id}`).then((r) => r.data),
    enabled: !!id,
  });

  const [form, setForm] = useState<TenantUpdateForm>({
    razon_social: "",
    nombre_comercial: "",
    ambiente_sri: "PRUEBAS",
    estado: "TRIAL",
  });

  useEffect(() => {
    if (!tenant) return;
    setForm({
      razon_social: tenant.razon_social,
      nombre_comercial: tenant.nombre_comercial ?? "",
      ambiente_sri: tenant.ambiente_sri,
      estado: tenant.estado,
    });
  }, [tenant]);

  const updateMutation = useMutation({
    mutationFn: (data: UpdateTenantRequest) => apiClient.patch(`/tenants/${id}`, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenants"] });
      queryClient.invalidateQueries({ queryKey: ["tenant", id] });
      toast.success("Tenant actualizado correctamente");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "No se pudo actualizar el tenant")),
  });

  const submit = () => {
    const nextErrors = validateForm(form);
    setErrors(nextErrors);
    if (hasErrors(nextErrors)) return;
    updateMutation.mutate(form);
  };

  if (isLoading) return <LoadingState />;
  if (!tenant) return <p className="text-sm text-destructive">Tenant no encontrado</p>;

  return (
    <div className="max-w-xl space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" onClick={() => navigate(-1)}>
          Volver
        </Button>
        <h1 className="text-xl font-bold">{tenant.ruc}</h1>
        <Badge tone={tenantEstadoTone[tenant.estado]}>{tenant.estado}</Badge>
      </div>

      <Card>
        <CardContent className="space-y-4">
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
              value={form.nombre_comercial}
              onChange={(event) => setForm({ ...form, nombre_comercial: event.target.value })}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Estado">
              <Select value={form.estado} onChange={(event) => setForm({ ...form, estado: event.target.value as EstadoTenant })}>
                {ESTADOS.map((estado) => (
                  <option key={estado} value={estado}>
                    {estado}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Ambiente SRI">
              <Select
                value={form.ambiente_sri}
                onChange={(event) => setForm({ ...form, ambiente_sri: event.target.value as AmbienteSri })}
              >
                <option value="PRUEBAS">PRUEBAS</option>
                <option value="PRODUCCION">PRODUCCION</option>
              </Select>
            </Field>
          </div>
          <Button onClick={submit} isLoading={updateMutation.isPending}>
            Guardar cambios
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <h2 className="mb-2 text-sm font-semibold">Resumen</h2>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Comprobantes este mes</span>
            <span className="font-mono">{tenant.comprobantes_mes_actual}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
