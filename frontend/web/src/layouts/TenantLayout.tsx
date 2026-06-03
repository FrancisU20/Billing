import { AppShell, type AppNavItem } from "@/layouts/AppShell";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS: AppNavItem[] = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/comprobantes", label: "Comprobantes" },
  { to: "/configuracion", label: "Configuración" },
];

export function TenantLayout() {
  const { user, logout } = useAuth();
  return <AppShell navItems={NAV_ITEMS} userEmail={user?.email} onLogout={logout} />;
}
