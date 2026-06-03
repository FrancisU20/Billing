import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { FullPageLoading } from "@/components/ui/LoadingState";

// Layouts
import { TenantLayout } from "@/layouts/TenantLayout";
import { SuperadminLayout } from "@/layouts/SuperadminLayout";

// Auth
import { LoginPage } from "@/pages/auth/LoginPage";

// Tenant pages
import { DashboardPage } from "@/pages/tenant/DashboardPage";
import { ComprobantesPage } from "@/pages/tenant/ComprobantesPage";
import { NuevoComprobantePage } from "@/pages/tenant/NuevoComprobantePage";
import { ComprobanteDetallePage } from "@/pages/tenant/ComprobanteDetallePage";
import { ConfiguracionPage } from "@/pages/tenant/ConfiguracionPage";

// Superadmin pages
import { TenantsPage } from "@/pages/superadmin/TenantsPage";
import { TenantDetailPage } from "@/pages/superadmin/TenantDetailPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <FullPageLoading />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireSuperadmin({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <FullPageLoading />;
  if (!user?.isSuperadmin) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export function AppRouter() {
  return (
    <Routes>
      {/* Pública */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* Tenant — autenticado */}
      <Route element={<RequireAuth><TenantLayout /></RequireAuth>}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/comprobantes" element={<ComprobantesPage />} />
        <Route path="/comprobantes/nuevo" element={<NuevoComprobantePage />} />
        <Route path="/comprobantes/:id" element={<ComprobanteDetallePage />} />
        <Route path="/configuracion" element={<ConfiguracionPage />} />
      </Route>

      {/* Superadmin — autenticado + isSuperadmin */}
      <Route element={<RequireAuth><RequireSuperadmin><SuperadminLayout /></RequireSuperadmin></RequireAuth>}>
        <Route path="/tenants" element={<TenantsPage />} />
        <Route path="/tenants/:id" element={<TenantDetailPage />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
