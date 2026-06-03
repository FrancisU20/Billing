import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { apiClient } from "@/lib/api-client";
import { getApiErrorMessage } from "@/lib/api-errors";
import { formatComprobanteNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import { EstadoBadge } from "@/components/comprobantes/EstadoBadge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingState } from "@/components/ui/LoadingState";
import { useToast } from "@/components/ui/Toast";
import type {
  Comprobante,
  DownloadUrlResponse,
  EstadoComprobante,
  RetryComprobanteTipo,
} from "@codelabs-billing/shared";

const TIMELINE_ESTADOS: EstadoComprobante[] = [
  "QUEUED", "PROCESSING", "XML_SIGNED", "SENT_TO_SRI",
  "RECEIVED_BY_SRI", "PENDING_AUTHORIZATION", "AUTHORIZED", "EMAIL_SENT",
];

const ESTADOS_EN_PROGRESO: EstadoComprobante[] = ["QUEUED", "PROCESSING", "SENT_TO_SRI", "PENDING_AUTHORIZATION", "EMAIL_PENDING"];

export function ComprobanteDetallePage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data: comp, isLoading } = useQuery<Comprobante>({
    queryKey: ["comprobante", id],
    queryFn: () => apiClient.get<Comprobante>(`/comprobantes/${id}`).then((r) => r.data),
    refetchInterval: (query) => {
      const estado = (query.state.data as Comprobante | undefined)?.estado;
      return estado && ESTADOS_EN_PROGRESO.includes(estado) ? 3000 : false;
    },
    enabled: !!id,
  });

  const retryMutation = useMutation({
    mutationFn: (tipo: RetryComprobanteTipo) =>
      apiClient.patch(`/comprobantes/${id}/retry`, { tipo }).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comprobante", id] });
      toast.success("Acción enviada correctamente");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "No se pudo ejecutar la acción")),
  });

  const handleDescargar = async (tipo: "xml" | "pdf") => {
    const { data } = await apiClient.get<DownloadUrlResponse>(`/comprobantes/${id}/descargar/${tipo}`);
    window.open(data.url, "_blank");
  };

  if (isLoading) return <LoadingState />;
  if (!comp) return <p className="text-destructive text-sm">Comprobante no encontrado</p>;

  const estadoIdx = TIMELINE_ESTADOS.indexOf(comp.estado);

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold">
          Factura {formatComprobanteNumber(comp.establecimiento, comp.punto_emision, comp.secuencial)}
        </h1>
        <EstadoBadge estado={comp.estado} />
      </div>

      <Card>
        <CardContent>
        <h2 className="text-sm font-semibold mb-3">Estado del proceso</h2>
        <div className="flex items-center gap-0">
          {TIMELINE_ESTADOS.map((e, i) => {
            const done = i <= estadoIdx;
            const current = i === estadoIdx;
            return (
              <div key={e} className="flex items-center flex-1">
                <div className="flex flex-col items-center gap-1">
                  <div className={cn("h-3 w-3 rounded-full border-2",
                    current ? "border-primary bg-primary animate-pulse" :
                    done ? "border-success-foreground bg-success-foreground" : "border-border bg-background"
                  )} />
                  <span className={cn("w-14 text-center text-[9px] leading-tight", done ? "text-foreground" : "text-muted-foreground")}>
                    {e.replace(/_/g, " ")}
                  </span>
                </div>
                {i < TIMELINE_ESTADOS.length - 1 && (
                  <div className={cn("mb-4 h-0.5 flex-1", done && i < estadoIdx ? "bg-success-foreground" : "bg-border")} />
                )}
              </div>
            );
          })}
        </div>
        </CardContent>
      </Card>

      <Card className="divide-y divide-border">
        {[
          ["Clave de acceso", comp.clave_acceso ?? "—"],
          ["Número autorización", comp.numero_autorizacion ?? "—"],
          ["Referencia", comp.external_reference ?? "—"],
          ["Reintentos", String(comp.retry_count)],
          ...(comp.error_detalle ? [["Error", comp.error_detalle]] : []),
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between px-4 py-2 text-sm">
            <span className="font-medium text-muted-foreground">{label}</span>
            <span className="font-mono text-xs max-w-[300px] text-right truncate">{value}</span>
          </div>
        ))}
      </Card>

      <div className="flex flex-wrap gap-2">
        {comp.numero_autorizacion && (
          <>
            <Button variant="outline" size="sm" onClick={() => handleDescargar("xml")}>Descargar XML</Button>
            <Button variant="outline" size="sm" onClick={() => handleDescargar("pdf")}>Descargar PDF</Button>
          </>
        )}
        {["RETURNED_BY_SRI", "FAILED"].includes(comp.estado) && (
          <Button size="sm" onClick={() => retryMutation.mutate("REENVIAR_SRI")} isLoading={retryMutation.isPending}>Reenviar al SRI</Button>
        )}
        {["NOT_AUTHORIZED", "MANUAL_REVIEW_REQUIRED"].includes(comp.estado) && (
          <Button size="sm" onClick={() => retryMutation.mutate("RECONSULTAR_AUTORIZACION")} isLoading={retryMutation.isPending}>Reconsultar</Button>
        )}
        {["EMAIL_FAILED", "AUTHORIZED"].includes(comp.estado) && (
          <Button variant="outline" size="sm" onClick={() => retryMutation.mutate("REENVIAR_EMAIL")} isLoading={retryMutation.isPending}>Reenviar email</Button>
        )}
      </div>
    </div>
  );
}
