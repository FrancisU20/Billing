import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiClient } from "@/lib/api-client";
import { getApiErrorMessage } from "@/lib/api-errors";
import { exactDigits, hasErrors, parseSelectValue, required, type FieldErrors } from "@/lib/validation";
import { tenantEstadoTone } from "@/lib/status-styles";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Field, Input, Select } from "@/components/ui/Form";
import { LoadingState } from "@/components/ui/LoadingState";
import { Table, TableHead, TableShell, Td, Th, Tr } from "@/components/ui/Table";
import { useToast } from "@/components/ui/Toast";
import { ambienteSriSchema } from "@codelabs-billing/shared";
import type { AmbienteSri, CreateTenantRequest, Tenant } from "@codelabs-billing/shared";

type TenantFormField = "ruc" | "razon_social";

const initialForm: CreateTenantRequest = {
  ruc: "",
  razon_social: "",
  nombre_comercial: "",
  ambiente_sri: "PRUEBAS",
};

function validateTenantForm(form: CreateTenantRequest): FieldErrors<TenantFormField> {
  return {
    ruc: exactDigits(form.ruc, 13, "RUC"),
    razon_social: required(form.razon_social, "Razón social"),
  };
}

export function TenantsPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateTenantRequest>(initialForm);
  const [errors, setErrors] = useState<FieldErrors<TenantFormField>>({});

  const { data: tenants = [], isLoading } = useQuery<Tenant[]>({
    queryKey: ["tenants"],
    queryFn: () => apiClient.get<Tenant[]>("/tenants").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: CreateTenantRequest) => apiClient.post<Tenant>("/tenants", data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenants"] });
      setShowForm(false);
      setForm(initialForm);
      setErrors({});
      toast.success("Tenant creado correctamente");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "No se pudo crear el tenant")),
  });

  const submit = () => {
    const nextErrors = validateTenantForm(form);
    setErrors(nextErrors);
    if (hasErrors(nextErrors)) return;
    createMutation.mutate(form);
  };

  if (isLoading) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-brand">Superadmin</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight">Tenants</h1>
        </div>
        <Button onClick={() => setShowForm(true)}>Nuevo tenant</Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="space-y-4">
            <h2 className="font-semibold">Nuevo tenant</h2>
            <div className="grid grid-cols-2 gap-4">
              <Field label="RUC *" error={errors.ruc}>
                <Input
                  maxLength={13}
                  value={form.ruc}
                  hasError={!!errors.ruc}
                  onChange={(event) => setForm({ ...form, ruc: event.target.value.replace(/\D/g, "") })}
                />
              </Field>
              <Field label="Ambiente SRI">
                <Select
                  value={form.ambiente_sri}
                  onChange={(event) => setForm({ ...form, ambiente_sri: parseSelectValue(ambienteSriSchema, event.target.value) })}
                >
                  <option value="PRUEBAS">PRUEBAS</option>
                  <option value="PRODUCCION">PRODUCCION</option>
                </Select>
              </Field>
              <Field label="Razón social *" error={errors.razon_social}>
                <Input
                  value={form.razon_social}
                  hasError={!!errors.razon_social}
                  onChange={(event) => setForm({ ...form, razon_social: event.target.value })}
                />
              </Field>
              <Field label="Nombre comercial">
                <Input
                  value={form.nombre_comercial ?? ""}
                  onChange={(event) => setForm({ ...form, nombre_comercial: event.target.value })}
                />
              </Field>
            </div>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setShowForm(false)}>
                Cancelar
              </Button>
              <Button onClick={submit} isLoading={createMutation.isPending}>
                Crear tenant
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <TableShell>
        <Table>
          <TableHead>
            <tr>
              <Th>RUC</Th>
              <Th>Razón social</Th>
              <Th>Estado</Th>
              <Th>Ambiente</Th>
              <Th className="text-right">Comp. mes</Th>
              <Th>Acciones</Th>
            </tr>
          </TableHead>
          <tbody>
            {tenants.map((tenant) => (
              <Tr key={tenant.id}>
                <Td className="font-mono text-xs">{tenant.ruc}</Td>
                <Td>{tenant.razon_social}</Td>
                <Td>
                  <Badge tone={tenantEstadoTone[tenant.estado]}>{tenant.estado}</Badge>
                </Td>
                <Td>
                  <Badge tone={tenant.ambiente_sri === "PRODUCCION" ? "success" : "warning"}>
                    {tenant.ambiente_sri}
                  </Badge>
                </Td>
                <Td className="text-right tabular-nums">{tenant.comprobantes_mes_actual}</Td>
                <Td>
                  <Link to={`/tenants/${tenant.id}`} className="text-xs text-primary underline-offset-2 hover:underline">
                    Ver
                  </Link>
                </Td>
              </Tr>
            ))}
            {!tenants.length && (
              <tr>
                <Td colSpan={6}>
                  <EmptyState message="No hay tenants" />
                </Td>
              </tr>
            )}
          </tbody>
        </Table>
      </TableShell>
    </div>
  );
}
