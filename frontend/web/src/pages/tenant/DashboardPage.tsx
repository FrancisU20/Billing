import { useAuth } from "@/lib/auth-context";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { getApiErrorMessage } from "@/lib/api-errors";
import { Link } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingState } from "@/components/ui/LoadingState";
import type { ComprobanteListResponse } from "@codelabs-billing/shared";

export function DashboardPage() {
  const { user } = useAuth();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["comprobantes", user?.tenantId, { limit: 1 }],
    queryFn: () =>
      apiClient.get<ComprobanteListResponse>("/comprobantes?limit=1").then((r) => r.data),
    enabled: !!user?.tenantId,
  });

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-brand">Panel operativo</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Bienvenido, {user?.email}</p>
      </div>
      {isLoading && <LoadingState />}
      {isError && (
        <Alert tone="danger">{getApiErrorMessage(error, "No se pudieron cargar los comprobantes")}</Alert>
      )}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Total comprobantes</p>
          <p className="text-4xl font-bold tracking-tight">{data?.total ?? "—"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-2">
          <Link to="/comprobantes/nuevo" className="block h-full">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Acción rápida</p>
            <p className="mt-3 text-sm font-bold text-primary">Emitir factura →</p>
          </Link>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Ambiente SRI</p>
          <p className="mt-3 text-sm font-bold">{user?.tenantId ? "Configurado" : "—"}</p>
          </CardContent>
        </Card>
      </div>
      <div>
        <h2 className="text-sm font-semibold mb-2">Accesos rápidos</h2>
        <div className="flex gap-2">
          <Link to="/comprobantes" className="text-xs text-primary underline-offset-2 hover:underline">Ver comprobantes →</Link>
          <Link to="/configuracion" className="text-xs text-primary underline-offset-2 hover:underline">Configuración →</Link>
        </div>
      </div>
    </div>
  );
}
