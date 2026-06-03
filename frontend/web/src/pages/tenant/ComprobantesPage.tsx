import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiClient } from "@/lib/api-client";
import { getApiErrorMessage } from "@/lib/api-errors";
import { formatComprobanteNumber } from "@/lib/format";
import { EstadoBadge } from "@/components/comprobantes/EstadoBadge";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { FilterChips, type FilterChip } from "@/components/ui/FilterChips";
import { LoadingState } from "@/components/ui/LoadingState";
import { Table, TableHead, TableShell, Td, Th, Tr } from "@/components/ui/Table";
import type { ComprobanteListResponse, EstadoComprobante } from "@codelabs-billing/shared";

type EstadoFilter = EstadoComprobante | "";

const ESTADOS: FilterChip<EstadoFilter>[] = [
  { value: "", label: "Todos" },
  { value: "AUTHORIZED", label: "Autorizados" },
  { value: "QUEUED", label: "En cola" },
  { value: "NOT_AUTHORIZED", label: "No autorizados" },
  { value: "FAILED", label: "Fallidos" },
];

export function ComprobantesPage() {
  const [estado, setEstado] = useState<EstadoFilter>("");

  const { data, isLoading, isError, error } = useQuery<ComprobanteListResponse>({
    queryKey: ["comprobantes", { estado }],
    queryFn: () =>
      apiClient
        .get<ComprobanteListResponse>("/comprobantes", {
          params: { estado: estado || undefined },
        })
        .then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-brand">Facturación electrónica</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight">Comprobantes</h1>
        </div>
        <Link to="/comprobantes/nuevo">
          <Button>Emitir factura</Button>
        </Link>
      </div>

      <FilterChips items={ESTADOS} value={estado} onChange={setEstado} />

      {isError && (
        <Alert tone="danger">{getApiErrorMessage(error, "No se pudieron cargar los comprobantes")}</Alert>
      )}
      {isLoading ? (
        <LoadingState />
      ) : (
        <TableShell>
          <Table>
            <TableHead>
              <tr>
                <Th>Número</Th>
                <Th>Referencia</Th>
                <Th>Estado</Th>
                <Th>Acciones</Th>
              </tr>
            </TableHead>
            <tbody>
              {(data?.items ?? []).map((comp) => (
                <Tr key={comp.id}>
                  <Td className="font-mono text-xs">
                    {formatComprobanteNumber(comp.establecimiento, comp.punto_emision, comp.secuencial)}
                  </Td>
                  <Td className="text-xs text-muted-foreground">{comp.external_reference ?? "—"}</Td>
                  <Td>
                    <EstadoBadge estado={comp.estado} />
                  </Td>
                  <Td>
                    <Link to={`/comprobantes/${comp.id}`} className="text-xs text-primary underline-offset-2 hover:underline">
                      Ver
                    </Link>
                  </Td>
                </Tr>
              ))}
              {!data?.items?.length && (
                <tr>
                  <Td colSpan={4}>
                    <EmptyState message="No hay comprobantes" />
                  </Td>
                </tr>
              )}
            </tbody>
          </Table>
        </TableShell>
      )}
    </div>
  );
}
