"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { EstadoBadge } from "@/components/comprobantes/EstadoBadge";
import type { Comprobante } from "@codelabs-billing/shared";

const TIMELINE_ESTADOS = [
  "QUEUED", "PROCESSING", "XML_SIGNED", "SENT_TO_SRI",
  "RECEIVED_BY_SRI", "PENDING_AUTHORIZATION", "AUTHORIZED", "EMAIL_SENT",
];

export default function ComprobanteDetallePage({ params }: { params: { id: string } }) {
  const queryClient = useQueryClient();
  const { data: comp, isLoading } = useQuery<Comprobante>({
    queryKey: ["comprobante", params.id],
    queryFn: () => apiClient.get<Comprobante>(`/comprobantes/${params.id}`).then((r) => r.data),
    refetchInterval: (data) =>
      ["QUEUED", "PROCESSING", "SENT_TO_SRI", "PENDING_AUTHORIZATION", "EMAIL_PENDING"].includes(
        (data as Comprobante)?.estado
      )
        ? 3000
        : false,
  });

  const retryMutation = useMutation({
    mutationFn: (tipo: string) =>
      apiClient.patch(`/comprobantes/${params.id}/retry`, { tipo }).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["comprobante", params.id] }),
  });

  const handleDescargar = async (tipo: "xml" | "pdf") => {
    const { data } = await apiClient.get<{ url: string }>(`/comprobantes/${params.id}/descargar/${tipo}`);
    window.open(data.url, "_blank");
  };

  if (isLoading) return <p className="text-muted-foreground text-sm">Cargando...</p>;
  if (!comp) return <p className="text-destructive text-sm">Comprobante no encontrado</p>;

  const estadoIdx = TIMELINE_ESTADOS.indexOf(comp.estado);

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold">
          Factura {comp.establecimiento}-{comp.punto_emision}-{comp.secuencial?.padStart(9, "0")}
        </h1>
        <EstadoBadge estado={comp.estado} />
      </div>

      {/* Timeline */}
      <div className="rounded-lg border border-border p-4">
        <h2 className="text-sm font-semibold mb-3">Estado del proceso</h2>
        <div className="flex items-center gap-0">
          {TIMELINE_ESTADOS.map((e, i) => {
            const done = i <= estadoIdx;
            const current = i === estadoIdx;
            return (
              <div key={e} className="flex items-center flex-1">
                <div className="flex flex-col items-center gap-1">
                  <div
                    className={`w-3 h-3 rounded-full border-2 ${
                      current
                        ? "border-primary bg-primary animate-pulse"
                        : done
                        ? "border-green-500 bg-green-500"
                        : "border-border bg-background"
                    }`}
                  />
                  <span className={`text-[9px] text-center leading-tight w-14 ${done ? "text-foreground" : "text-muted-foreground"}`}>
                    {e.replace(/_/g, " ")}
                  </span>
                </div>
                {i < TIMELINE_ESTADOS.length - 1 && (
                  <div className={`flex-1 h-0.5 mb-4 ${done && i < estadoIdx ? "bg-green-500" : "bg-border"}`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Info */}
      <div className="rounded-lg border border-border divide-y divide-border">
        {[
          ["Clave de acceso", comp.clave_acceso ?? "—"],
          ["Número autorización", comp.numero_autorizacion ?? "—"],
          ["Receptor", (comp as any).datos?.razon_social_comprador ?? "—"],
          ["Identificación", (comp as any).datos?.identificacion_comprador ?? "—"],
          ["Total", `$${(comp as any).datos?.importe_total ?? "—"}`],
          ["Reintentos", String(comp.retry_count)],
          ...(comp.error_detalle ? [["Error", comp.error_detalle]] : []),
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between px-4 py-2 text-sm">
            <span className="font-medium text-muted-foreground">{label}</span>
            <span className="font-mono text-xs max-w-[300px] text-right truncate">{value}</span>
          </div>
        ))}
      </div>

      {/* Acciones */}
      <div className="flex flex-wrap gap-2">
        {comp.numero_autorizacion && (
          <>
            <button
              onClick={() => handleDescargar("xml")}
              className="rounded-md border border-input px-3 py-1.5 text-sm hover:bg-muted"
            >
              Descargar XML
            </button>
            <button
              onClick={() => handleDescargar("pdf")}
              className="rounded-md border border-input px-3 py-1.5 text-sm hover:bg-muted"
            >
              Descargar PDF
            </button>
          </>
        )}
        {["RETURNED_BY_SRI", "FAILED"].includes(comp.estado) && (
          <button
            onClick={() => retryMutation.mutate("REENVIAR_SRI")}
            disabled={retryMutation.isPending}
            className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            Reenviar al SRI
          </button>
        )}
        {["NOT_AUTHORIZED", "MANUAL_REVIEW_REQUIRED"].includes(comp.estado) && (
          <button
            onClick={() => retryMutation.mutate("RECONSULTAR_AUTORIZACION")}
            disabled={retryMutation.isPending}
            className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            Reconsultar autorización
          </button>
        )}
        {["EMAIL_FAILED", "AUTHORIZED"].includes(comp.estado) && (
          <button
            onClick={() => retryMutation.mutate("REENVIAR_EMAIL")}
            disabled={retryMutation.isPending}
            className="rounded-md border border-input px-3 py-1.5 text-sm hover:bg-muted"
          >
            Reenviar email
          </button>
        )}
      </div>
    </div>
  );
}
