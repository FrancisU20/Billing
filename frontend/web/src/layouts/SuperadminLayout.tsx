import { AppShell, type AppNavItem } from "@/layouts/AppShell";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS: AppNavItem[] = [
  { to: "/tenants", label: "Tenants" },
];

export function SuperadminLayout() {
  const { user, logout } = useAuth();
  return <AppShell navItems={NAV_ITEMS} userEmail={user?.email} eyebrow="Superadmin" onLogout={logout} />;
}
