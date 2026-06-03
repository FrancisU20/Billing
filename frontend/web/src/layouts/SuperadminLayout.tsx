import { Outlet, NavLink } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { to: "/tenants", label: "Tenants" },
];

export function SuperadminLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="w-64 border-r border-border bg-card flex flex-col">
        <div className="p-4 border-b border-border">
          <p className="text-xs font-bold text-primary">CodeLabs Billing</p>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mt-1">Superadmin</p>
          <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
        </div>
        <nav className="flex-1 p-3 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive ? "bg-accent font-medium" : "hover:bg-accent"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-border">
          <button
            onClick={logout}
            className="w-full rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent text-left"
          >
            Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
