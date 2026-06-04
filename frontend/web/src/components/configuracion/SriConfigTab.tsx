"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, Pencil, PowerOff, Power, Check, X } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { getApiErrorMessage } from "@/lib/api-errors";
import { exactDigits, hasErrors, type FieldErrors } from "@/lib/validation";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Field, Input } from "@/components/ui/Form";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils";
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
  const [showInactive, setShowInactive] = useState(false);
  const [estErrors, setEstErrors] = useState<FieldErrors<EstablecimientoField>>({});

  // Edición inline de establecimiento
  const [editingEst, setEditingEst] = useState<string | null>(null);
  const [editDireccion, setEditDireccion] = useState("");

  const invalidateEst = () => queryClient.invalidateQueries({ queryKey: ["establecimientos", tenantId] });
  const invalidatePto = (estCodigo: string) =>
    queryClient.invalidateQueries({ queryKey: ["puntos-emision", tenantId, estCodigo] });

  // ── Queries ──────────────────────────────────────────────────────────────
  const { data: establecimientos = [] } = useQuery<Establecimiento[]>({
    queryKey: ["establecimientos", tenantId, showInactive],
    queryFn: () =>
      apiClient
        .get<Establecimiento[]>(`/tenants/${tenantId}/establecimientos`, {
          params: { include_inactive: showInactive },
        })
        .then((r) => r.data),
    enabled: !!tenantId,
  });

  const { data: puntosMap } = useQuery<Record<string, PuntoEmision[]>>({
    queryKey: ["puntos-emision", tenantId, expandedEst, showInactive],
    queryFn: async () => {
      if (!expandedEst) return {};
      const r = await apiClient.get<PuntoEmision[]>(
        `/tenants/${tenantId}/establecimientos/${expandedEst}/puntos-emision`,
        { params: { include_inactive: showInactive } }
      );
      return { [expandedEst]: r.data };
    },
    enabled: !!expandedEst,
  });

  // ── Mutations ─────────────────────────────────────────────────────────────
  const createEst = useMutation({
    mutationFn: (data: CreateEstablecimientoRequest) =>
      apiClient.post(`/tenants/${tenantId}/establecimientos`, data),
    onSuccess: () => { invalidateEst(); setNewEst({ codigo: "", direccion: "" }); setEstErrors({}); toast.success("Establecimiento creado"); },
    onError: (e) => toast.error(getApiErrorMessage(e, "No se pudo crear el establecimiento")),
  });

  const updateEst = useMutation({
    mutationFn: ({ codigo, direccion }: { codigo: string; direccion: string }) =>
      apiClient.patch(`/tenants/${tenantId}/establecimientos/${codigo}`, { direccion }),
    onSuccess: () => { invalidateEst(); setEditingEst(null); toast.success("Dirección actualizada"); },
    onError: (e) => toast.error(getApiErrorMessage(e, "No se pudo actualizar")),
  });

  const deactivateEst = useMutation({
    mutationFn: (codigo: string) =>
      apiClient.delete(`/tenants/${tenantId}/establecimientos/${codigo}`),
    onSuccess: (_, codigo) => { invalidateEst(); if (expandedEst === codigo) setExpandedEst(null); toast.success("Establecimiento desactivado"); },
    onError: (e) => toast.error(getApiErrorMessage(e, "No se pudo desactivar")),
  });

  const activateEst = useMutation({
    mutationFn: (codigo: string) =>
      apiClient.post(`/tenants/${tenantId}/establecimientos/${codigo}/activar`),
    onSuccess: () => { invalidateEst(); toast.success("Establecimiento activado"); },
    onError: (e) => toast.error(getApiErrorMessage(e, "No se pudo activar")),
  });

  const createPto = useMutation({
    mutationFn: ({ estCodigo, ptoCodigo }: { estCodigo: string; ptoCodigo: string }) =>
      apiClient.post(`/tenants/${tenantId}/establecimientos/${estCodigo}/puntos-emision`, { codigo: ptoCodigo }),
    onSuccess: (_, vars) => { invalidatePto(vars.estCodigo); setNewPto((p) => ({ ...p, [vars.estCodigo]: "" })); toast.success("Punto de emisión creado"); },
    onError: (e) => toast.error(getApiErrorMessage(e, "No se pudo crear el punto de emisión")),
  });

  const deactivatePto = useMutation({
    mutationFn: ({ estCodigo, ptoCodigo }: { estCodigo: string; ptoCodigo: string }) =>
      apiClient.delete(`/tenants/${tenantId}/establecimientos/${estCodigo}/puntos-emision/${ptoCodigo}`),
    onSuccess: (_, vars) => { invalidatePto(vars.estCodigo); toast.success("Punto de emisión desactivado"); },
    onError: (e) => toast.error(getApiErrorMessage(e, "No se pudo desactivar")),
  });

  const activatePto = useMutation({
    mutationFn: ({ estCodigo, ptoCodigo }: { estCodigo: string; ptoCodigo: string }) =>
      apiClient.post(`/tenants/${tenantId}/establecimientos/${estCodigo}/puntos-emision/${ptoCodigo}/activar`),
    onSuccess: (_, vars) => { invalidatePto(vars.estCodigo); toast.success("Punto de emisión activado"); },
    onError: (e) => toast.error(getApiErrorMessage(e, "No se pudo activar")),
  });

  const submitEstablecimiento = () => {
    const nextErrors = { codigo: exactDigits(newEst.codigo, 3, "Código") };
    setEstErrors(nextErrors);
    if (hasErrors(nextErrors)) return;
    createEst.mutate(newEst);
  };

  const activeEst = establecimientos.filter((e) => e.estado === "ACTIVE");
  const inactiveEst = establecimientos.filter((e) => e.estado !== "ACTIVE");

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="font-semibold">Establecimientos y puntos de emisión</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Configura los establecimientos y puntos de emisión de tu empresa ante el SRI.
        </p>
      </div>

      {/* Formulario nuevo establecimiento */}
      <Card className="space-y-3 p-4">
        <h3 className="text-sm font-medium">Nuevo establecimiento</h3>
        <div className="flex gap-2">
          <Field error={estErrors.codigo}>
            <Input className="w-20" placeholder="001" maxLength={3}
              value={newEst.codigo} hasError={!!estErrors.codigo}
              onChange={(e) => setNewEst({ ...newEst, codigo: e.target.value.replace(/\D/g, "") })} />
          </Field>
          <Input className="flex-1" placeholder="Dirección del establecimiento"
            value={newEst.direccion ?? ""}
            onChange={(e) => setNewEst({ ...newEst, direccion: e.target.value })} />
          <Button onClick={submitEstablecimiento} isLoading={createEst.isPending}>Agregar</Button>
        </div>
      </Card>

      {/* Lista de establecimientos activos */}
      <div className="space-y-2">
        {activeEst.map((est) => (
          <Card key={est.codigo} className="overflow-hidden">
            {/* Cabecera del establecimiento */}
            <div className="flex items-center bg-muted/30 hover:bg-muted/40">
              <button
                onClick={() => setExpandedEst(expandedEst === est.codigo ? null : est.codigo)}
                aria-expanded={expandedEst === est.codigo}
                aria-controls={`est-${est.codigo}`}
                className="flex flex-1 items-center justify-between px-4 py-3 text-sm"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono font-semibold">{est.codigo}</span>

                  {/* Edición inline de dirección */}
                  {editingEst === est.codigo ? (
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <Input
                        className="h-7 w-52 text-xs"
                        value={editDireccion}
                        autoFocus
                        onChange={(e) => setEditDireccion(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") updateEst.mutate({ codigo: est.codigo, direccion: editDireccion });
                          if (e.key === "Escape") setEditingEst(null);
                        }}
                      />
                      <button onClick={() => updateEst.mutate({ codigo: est.codigo, direccion: editDireccion })}
                        className="rounded p-1 text-brand hover:bg-brand/10">
                        <Check className="h-3.5 w-3.5" aria-hidden />
                      </button>
                      <button onClick={() => setEditingEst(null)}
                        className="rounded p-1 text-muted-foreground hover:bg-muted">
                        <X className="h-3.5 w-3.5" aria-hidden />
                      </button>
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      {est.direccion || "Sin dirección"}
                    </span>
                  )}
                </div>
                {expandedEst === est.codigo
                  ? <ChevronUp className="h-4 w-4 text-muted-foreground" aria-hidden />
                  : <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden />}
              </button>

              {/* Acciones establecimiento activo */}
              <div className="flex items-center gap-1 pr-3">
                <button onClick={(e) => { e.stopPropagation(); setEditingEst(est.codigo); setEditDireccion(est.direccion ?? ""); }}
                  aria-label="Editar dirección"
                  className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground">
                  <Pencil className="h-3.5 w-3.5" aria-hidden />
                </button>
                <button onClick={(e) => { e.stopPropagation(); if (window.confirm(`¿Desactivar establecimiento ${est.codigo} y sus puntos de emisión?`)) deactivateEst.mutate(est.codigo); }}
                  aria-label="Desactivar establecimiento"
                  className="rounded p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive">
                  <PowerOff className="h-3.5 w-3.5" aria-hidden />
                </button>
              </div>
            </div>

            {/* Puntos de emisión */}
            {expandedEst === est.codigo && (
              <div id={`est-${est.codigo}`} className="space-y-3 px-4 py-3">
                <div className="space-y-1">
                  {(puntosMap?.[est.codigo] ?? []).map((pto) => {
                    const isActive = pto.estado === "ACTIVE";
                    return (
                      <div key={pto.codigo}
                        className={cn("flex items-center justify-between gap-2 rounded px-2 py-1 text-sm",
                          !isActive && "opacity-50")}>
                        <div className="flex items-center gap-2">
                          <span className={cn("rounded px-2 py-0.5 font-mono text-xs",
                            isActive ? "bg-muted" : "bg-muted/50 line-through")}>
                            {est.codigo}-{pto.codigo}
                          </span>
                          {!isActive && (
                            <span className="rounded-full border border-muted-foreground/30 px-2 py-0.5 text-xs text-muted-foreground">
                              INACTIVO
                            </span>
                          )}
                        </div>
                        {isActive ? (
                          <button
                            onClick={() => { if (window.confirm(`¿Desactivar punto ${est.codigo}-${pto.codigo}?`)) deactivatePto.mutate({ estCodigo: est.codigo, ptoCodigo: pto.codigo }); }}
                            aria-label="Desactivar punto de emisión"
                            className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive">
                            <PowerOff className="h-3.5 w-3.5" aria-hidden />
                          </button>
                        ) : (
                          <button
                            onClick={() => activatePto.mutate({ estCodigo: est.codigo, ptoCodigo: pto.codigo })}
                            aria-label="Activar punto de emisión"
                            className="rounded p-1 text-muted-foreground hover:bg-brand/10 hover:text-brand">
                            <Power className="h-3.5 w-3.5" aria-hidden />
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>

                <div className="flex gap-2 pt-1">
                  <Input className="w-20 text-xs" placeholder="001" maxLength={3}
                    value={newPto[est.codigo] ?? ""}
                    onChange={(e) => setNewPto((p) => ({ ...p, [est.codigo]: e.target.value.replace(/\D/g, "") }))} />
                  <Button variant="outline" size="sm"
                    onClick={() => createPto.mutate({ estCodigo: est.codigo, ptoCodigo: newPto[est.codigo] ?? "" })}
                    disabled={!newPto[est.codigo] || (newPto[est.codigo] ?? "").length !== 3}
                    isLoading={createPto.isPending}>
                    Agregar punto
                  </Button>
                </div>
              </div>
            )}
          </Card>
        ))}

        {activeEst.length === 0 && (
          <EmptyState message="No hay establecimientos configurados. Agrega uno para poder emitir comprobantes." />
        )}
      </div>

      {/* Toggle inactivos */}
      <div>
        <button
          onClick={() => setShowInactive((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          {showInactive
            ? <ChevronUp className="h-3.5 w-3.5" aria-hidden />
            : <ChevronDown className="h-3.5 w-3.5" aria-hidden />}
          {showInactive ? "Ocultar inactivos" : `Mostrar inactivos${inactiveEst.length > 0 ? ` (${inactiveEst.length})` : ""}`}
        </button>

        {showInactive && inactiveEst.length > 0 && (
          <div className="mt-2 space-y-1.5">
            {inactiveEst.map((est) => (
              <div key={est.codigo}
                className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/20 px-4 py-2.5 opacity-60">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm font-medium line-through">{est.codigo}</span>
                  {est.direccion && <span className="text-xs text-muted-foreground">{est.direccion}</span>}
                  <span className="rounded-full border border-muted-foreground/30 px-2 py-0.5 text-xs text-muted-foreground">
                    INACTIVO
                  </span>
                </div>
                <button
                  onClick={() => activateEst.mutate(est.codigo)}
                  aria-label={`Activar establecimiento ${est.codigo}`}
                  className="flex items-center gap-1 rounded px-2 py-1 text-xs text-muted-foreground hover:bg-brand/10 hover:text-brand">
                  <Power className="h-3.5 w-3.5" aria-hidden />
                  Activar
                </button>
              </div>
            ))}
          </div>
        )}

        {showInactive && inactiveEst.length === 0 && (
          <p className="mt-2 text-xs text-muted-foreground">No hay establecimientos inactivos.</p>
        )}
      </div>
    </div>
  );
}
