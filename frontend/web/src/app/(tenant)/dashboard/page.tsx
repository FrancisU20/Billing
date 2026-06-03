"use client";

import { useAuth } from "@/lib/auth-context";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import Link from "next/link";

export default function DashboardPage() {
  const { user } = useAuth();

  const { data } = useQuery({
    queryKey: ["comprobantes-summary", user?.tenantId],
    queryFn: () =>
      apiClient
        .get<{ total: number; items: unknown[] }>("/comprobantes?limit=5")
        .then((r) => r.data),
    enabled: !!user?.tenantId,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Bienvenido, {user?.email}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-border p-4">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Total comprobantes</p>
          <p className="text-3xl font-bold mt-1">{data?.total ?? "—"}</p>
        </div>
        <div className="rounded-lg border border-border p-4">
          <Link href="/comprobantes/nuevo" className="block h-full">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Acción rápida</p>
            <p className="text-sm font-medium mt-2 text-primary">+ Emitir factura →</p>
          </Link>
        </div>
        <div className="rounded-lg border border-border p-4">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Ambiente SRI</p>
          <p className="text-sm font-medium mt-2">
            {user?.tenantId ? "Configurado" : "—"}
          </p>
        </div>
      </div>

      <div>
        <h2 className="text-sm font-semibold mb-3">Últimos comprobantes</h2>
        <Link
          href="/comprobantes"
          className="text-xs text-primary underline-offset-2 hover:underline"
        >
          Ver todos →
        </Link>
      </div>
    </div>
  );
}
