"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { getApiErrorMessage } from "@/lib/api-errors";
import { exactDigits, hasErrors, type FieldErrors } from "@/lib/validation";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Field, Input } from "@/components/ui/Form";
import { useToast } from "@/components/ui/Toast";
import type {
  CreateEstablecimientoRequest,
  Establecimiento,
  PuntoEmision,
} from "@codelabs-billing/shared";

type EstablecimientoField = "codigo";

export function SriConfigTab() {
  const { user } = useAuth();
  const tenantId = user?.tenantId ?? "";
  const queryClient = useQueryClient();
  const toast = useToast();
  const [newEst, setNewEst] = useState<CreateEstablecimientoRequest>({ codigo: "", direccion: "" });
  const [newPto, setNewPto] = useState<Record<string, string>>({});
  const [expandedEst, setExpandedEst] = useState<string | null>(null);
  const [estErrors, setEstErrors] = useState<FieldErrors<EstablecimientoField>>({});

  const { data: establecimientos = [] } = useQuery<Establecimiento[]>({
    queryKey: ["establecimientos", tenantId],
    queryFn: () =>
      apiClient.get<Establecimiento[]>(`/tenants/${tenantId}/establecimientos`).then((r) => r.data),
    enabled: !!tenantId,
  });

  const { data: puntosMap } = useQuery<Record<string, PuntoEmision[]>>({
    queryKey: ["puntos-emision", tenantId, expandedEst],
    queryFn: async () => {
      if (!expandedEst) return {};
      const r = await apiClient.get<PuntoEmision[]>(
        `/tenants/${tenantId}/establecimientos/${expandedEst}/puntos-emision`
      );
      return { [expandedEst]: r.data };
    },
    enabled: !!expandedEst,
  });

  const createEst = useMutation({
    mutationFn: (data: CreateEstablecimientoRequest) =>
      apiClient.post(`/tenants/${tenantId}/establecimientos`, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["establecimientos", tenantId] });
      setNewEst({ codigo: "", direccion: "" });
      setEstErrors({});
      toast.success("Establecimiento creado");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "No se pudo crear el establecimiento")),
  });

  const deleteEst = useMutation({
    mutationFn: (codigo: string) =>
      apiClient.delete(`/tenants/${tenantId}/establecimientos/${codigo}`),
    onSuccess: (_, codigo) => {
      queryClient.invalidateQueries({ queryKey: ["establecimientos", tenantId] });
      if (expandedEst === codigo) setExpandedEst(null);
      toast.success("Establecimiento eliminado");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "No se pudo eliminar el establecimiento")),
  });

  const createPto = useMutation({
    mutationFn: ({ estCodigo, ptoCodigo }: { estCodigo: string; ptoCodigo: string }) =>
      apiClient
        .post(`/tenants/${tenantId}/establecimientos/${estCodigo}/puntos-emision`, { codigo: ptoCodigo })
        .then((r) => r.data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ["puntos-emision", tenantId, vars.estCodigo] });
      setNewPto((prev) => ({ ...prev, [vars.estCodigo]: "" }));
      toast.success("Punto de emisión creado");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "No se pudo crear el punto de emisión")),
  });

  const deletePto = useMutation({
    mutationFn: ({ estCodigo, ptoCodigo }: { estCodigo: string; ptoCodigo: string }) =>
      apiClient.delete(`/tenants/${tenantId}/establecimientos/${estCodigo}/puntos-emision/${ptoCodigo}`),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ["puntos-emision", tenantId, vars.estCodigo] });
      toast.success("Punto de emisión eliminado");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "No se pudo eliminar el punto de emisión")),
  });

  const submitEstablecimiento = () => {
    const nextErrors = { codigo: exactDigits(newEst.codigo, 3, "Código") };
    setEstErrors(nextErrors);
    if (hasErrors(nextErrors)) return;
    createEst.mutate(newEst);
  };

  const confirmDelete = (message: string, onConfirm: () => void) => {
    if (window.confirm(message)) onConfirm();
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="font-semibold">Establecimientos y puntos de emisión</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Configura los establecimientos y puntos de emisión de tu empresa ante el SRI.
        </p>
      </div>

      <Card className="space-y-3 p-4">
        <h3 className="text-sm font-medium">Nuevo establecimiento</h3>
        <div className="flex gap-2">
          <Field error={estErrors.codigo}>
            <Input
              className="w-20"
              placeholder="001"
              maxLength={3}
              value={newEst.codigo}
              hasError={!!estErrors.codigo}
              onChange={(event) => setNewEst({ ...newEst, codigo: event.target.value.replace(/\D/g, "") })}
            />
          </Field>
          <Input
            className="flex-1"
            placeholder="Dirección del establecimiento"
            value={newEst.direccion ?? ""}
            onChange={(event) => setNewEst({ ...newEst, direccion: event.target.value })}
          />
          <Button onClick={submitEstablecimiento} isLoading={createEst.isPending}>
            Agregar
          </Button>
        </div>
      </Card>

      <div className="space-y-2">
        {establecimientos.map((est) => (
          <Card key={est.codigo} className="overflow-hidden">
            <div className="flex items-center bg-muted/30 text-sm hover:bg-muted/50">
              <button
                onClick={() => setExpandedEst(expandedEst === est.codigo ? null : est.codigo)}
                aria-expanded={expandedEst === est.codigo}
                aria-controls={`est-content-${est.codigo}`}
                className="flex flex-1 items-center justify-between px-4 py-3"
              >
                <span className="font-mono font-medium">
                  Establecimiento {est.codigo}
                  {est.direccion && <span className="ml-2 font-normal text-muted-foreground">{est.direccion}</span>}
                </span>
                {expandedEst === est.codigo ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                )}
              </button>
              <button
                onClick={() => confirmDelete(
                  `¿Eliminar establecimiento ${est.codigo} y todos sus puntos de emisión?`,
                  () => deleteEst.mutate(est.codigo)
                )}
                aria-label={`Eliminar establecimiento ${est.codigo}`}
                className="px-3 py-3 text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            {expandedEst === est.codigo && (
              <div id={`est-content-${est.codigo}`} className="space-y-3 px-4 py-3">
                <div className="space-y-1">
                  {(puntosMap?.[est.codigo] ?? []).map((pto) => (
                    <div key={pto.codigo} className="flex items-center justify-between gap-2 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs">
                          {est.codigo}-{pto.codigo}
                        </span>
                        <span className="text-xs text-muted-foreground">Punto de emisión activo</span>
                      </div>
                      <button
                        onClick={() => confirmDelete(
                          `¿Eliminar punto de emisión ${est.codigo}-${pto.codigo}?`,
                          () => deletePto.mutate({ estCodigo: est.codigo, ptoCodigo: pto.codigo })
                        )}
                        aria-label={`Eliminar punto de emisión ${pto.codigo}`}
                        className="text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </div>
                  ))}
                </div>

                <div className="flex gap-2 pt-1">
                  <Input
                    className="w-20 text-xs"
                    placeholder="001"
                    maxLength={3}
                    value={newPto[est.codigo] ?? ""}
                    onChange={(event) =>
                      setNewPto((prev) => ({ ...prev, [est.codigo]: event.target.value.replace(/\D/g, "") }))
                    }
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => createPto.mutate({ estCodigo: est.codigo, ptoCodigo: newPto[est.codigo] ?? "" })}
                    disabled={!newPto[est.codigo] || (newPto[est.codigo] ?? "").length !== 3}
                    isLoading={createPto.isPending}
                  >
                    Agregar punto
                  </Button>
                </div>
              </div>
            )}
          </Card>
        ))}

        {establecimientos.length === 0 && (
          <EmptyState message="No hay establecimientos configurados. Agrega uno para poder emitir comprobantes." />
        )}
      </div>
    </div>
  );
}
