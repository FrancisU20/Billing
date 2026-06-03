"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

interface Establecimiento {
  id: string;
  codigo: string;
  direccion: string | null;
  estado: string;
}

interface PuntoEmision {
  id: string;
  codigo: string;
  estado: string;
}

export function SriConfigTab() {
  const { user } = useAuth();
  const tenantId = user?.tenantId ?? "";
  const queryClient = useQueryClient();
  const [newEst, setNewEst] = useState({ codigo: "", direccion: "" });
  const [newPto, setNewPto] = useState<Record<string, string>>({});
  const [expandedEst, setExpandedEst] = useState<string | null>(null);

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
    mutationFn: (data: { codigo: string; direccion: string }) =>
      apiClient.post(`/tenants/${tenantId}/establecimientos`, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["establecimientos", tenantId] });
      setNewEst({ codigo: "", direccion: "" });
    },
  });

  const createPto = useMutation({
    mutationFn: ({ estCodigo, ptoCodigo }: { estCodigo: string; ptoCodigo: string }) =>
      apiClient
        .post(`/tenants/${tenantId}/establecimientos/${estCodigo}/puntos-emision`, { codigo: ptoCodigo })
        .then((r) => r.data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ["puntos-emision", tenantId, vars.estCodigo] });
      setNewPto((prev) => ({ ...prev, [vars.estCodigo]: "" }));
    },
  });

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="font-semibold">Establecimientos y puntos de emisión</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Configura los establecimientos y puntos de emisión de tu empresa ante el SRI.
        </p>
      </div>

      {/* Crear establecimiento */}
      <div className="rounded-lg border border-border p-4 space-y-3">
        <h3 className="text-sm font-medium">Nuevo establecimiento</h3>
        <div className="flex gap-2">
          <input
            className="w-20 rounded border border-input bg-background px-2 py-1 text-sm"
            placeholder="001"
            maxLength={3}
            value={newEst.codigo}
            onChange={(e) => setNewEst({ ...newEst, codigo: e.target.value })}
          />
          <input
            className="flex-1 rounded border border-input bg-background px-2 py-1 text-sm"
            placeholder="Dirección del establecimiento"
            value={newEst.direccion}
            onChange={(e) => setNewEst({ ...newEst, direccion: e.target.value })}
          />
          <button
            onClick={() => createEst.mutate(newEst)}
            disabled={!newEst.codigo || createEst.isPending}
            className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            Agregar
          </button>
        </div>
      </div>

      {/* Lista de establecimientos */}
      <div className="space-y-2">
        {establecimientos.map((est) => (
          <div key={est.codigo} className="rounded-lg border border-border overflow-hidden">
            <button
              onClick={() => setExpandedEst(expandedEst === est.codigo ? null : est.codigo)}
              className="w-full flex items-center justify-between px-4 py-3 text-sm bg-muted/30 hover:bg-muted/50"
            >
              <span className="font-medium font-mono">
                Establecimiento {est.codigo}
                {est.direccion && <span className="font-normal text-muted-foreground ml-2">— {est.direccion}</span>}
              </span>
              <span className="text-muted-foreground text-xs">{expandedEst === est.codigo ? "▲" : "▼"}</span>
            </button>

            {expandedEst === est.codigo && (
              <div className="px-4 py-3 space-y-3">
                {/* Puntos de emisión */}
                <div className="space-y-1">
                  {(puntosMap?.[est.codigo] ?? []).map((pto) => (
                    <div key={pto.codigo} className="flex items-center gap-2 text-sm">
                      <span className="font-mono text-xs bg-muted px-2 py-0.5 rounded">
                        {est.codigo}-{pto.codigo}
                      </span>
                      <span className="text-muted-foreground text-xs">Punto de emisión activo</span>
                    </div>
                  ))}
                </div>

                {/* Agregar punto de emisión */}
                <div className="flex gap-2 pt-1">
                  <input
                    className="w-20 rounded border border-input bg-background px-2 py-1 text-xs"
                    placeholder="001"
                    maxLength={3}
                    value={newPto[est.codigo] ?? ""}
                    onChange={(e) => setNewPto((p) => ({ ...p, [est.codigo]: e.target.value }))}
                  />
                  <button
                    onClick={() =>
                      createPto.mutate({ estCodigo: est.codigo, ptoCodigo: newPto[est.codigo] ?? "" })
                    }
                    disabled={!newPto[est.codigo] || createPto.isPending}
                    className="rounded border border-primary px-2 py-1 text-xs text-primary hover:bg-primary/10 disabled:opacity-50"
                  >
                    + Punto de emisión
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}

        {establecimientos.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-4">
            No hay establecimientos configurados. Agrega uno para poder emitir comprobantes.
          </p>
        )}
      </div>
    </div>
  );
}
