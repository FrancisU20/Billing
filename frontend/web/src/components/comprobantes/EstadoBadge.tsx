import type { EstadoComprobante } from "@codelabs-billing/shared";
import { Badge } from "@/components/ui/Badge";
import { comprobanteEstadoTone } from "@/lib/status-styles";

export function EstadoBadge({ estado }: { estado: EstadoComprobante | string }) {
  const tone = comprobanteEstadoTone[estado as EstadoComprobante] ?? "neutral";
  return <Badge tone={tone}>{estado.replace(/_/g, " ")}</Badge>;
}
