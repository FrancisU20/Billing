"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { EstadoBadge } from "@/components/comprobantes/EstadoBadge";
import type { Comprobante } from "@codelabs-billing/shared";
import Link from "next/link";

export default function ComprobantesPage() {
  const [estado, setEstado] = useState("");

  const { data, isLoading } = useQuery<{ items: Comprobante[]; total: number }>({
    queryKey: ["comprobantes", estado],
    queryFn: () =>
      apiClient
        .get<{ items: Comprobante[]; total: number }>("/comprobantes", { params: { estado: estado || undefined } })
        .then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Comprobantes</h1>
        <Link
          href="/comprobantes/nuevo"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Emitir factura
        </Link>
      </div>

      <div className="flex gap-2">
        {["", "AUTHORIZED", "QUEUED", "NOT_AUTHORIZED", "FAILED"].map((e) => (
          <button
            key={e}
            onClick={() => setEstado(e)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              estado === e
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-accent"
            }`}
          >
            {e || "Todos"}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-muted-foreground text-sm">Cargando...</p>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Número</th>
                <th className="px-4 py-3 text-left font-medium">Receptor</th>
                <th className="px-4 py-3 text-left font-medium">Estado</th>
                <th className="px-4 py-3 text-left font-medium">Clave de acceso</th>
                <th className="px-4 py-3 text-left font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((comp) => (
                <tr key={comp.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-3 font-mono text-xs">
                    {comp.establecimiento}-{comp.punto_emision}-{comp.secuencial?.padStart(9, "0")}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {(comp as any).datos?.razon_social_comprador ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    <EstadoBadge estado={comp.estado} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground truncate max-w-[160px]">
                    {comp.clave_acceso ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/comprobantes/${comp.id}`}
                      className="text-xs text-primary underline-offset-2 hover:underline"
                    >
                      Ver
                    </Link>
                  </td>
                </tr>
              ))}
              {!data?.items?.length && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground text-sm">
                    No hay comprobantes
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
