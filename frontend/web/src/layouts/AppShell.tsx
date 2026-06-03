import { NavLink, Outlet } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export interface AppNavItem {
  to: string;
  label: string;
}

export function AppShell({
  userEmail,
  eyebrow,
  navItems,
  onLogout,
}: {
  userEmail?: string;
  eyebrow?: string;
  navItems: AppNavItem[];
  onLogout: () => void;
}) {
  return (
    <div className="flex min-h-screen bg-background">
      <aside className="flex w-64 flex-col bg-sidebar text-sidebar-foreground shadow-lift">
        <div className="border-b border-white/10 p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand text-sm font-black text-brand-foreground shadow-lift">
              CL
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-bold tracking-tight">CodeLabs Billing</p>
              {eyebrow && <p className="mt-0.5 text-[11px] font-semibold uppercase text-sidebar-muted">{eyebrow}</p>}
            </div>
          </div>
          <p className="mt-4 truncate text-xs text-sidebar-muted">{userEmail}</p>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-white text-primary shadow-control"
                    : "text-sidebar-muted hover:bg-white/10 hover:text-sidebar-foreground"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/10 p-3">
          <Button variant="ghost" onClick={onLogout} className="w-full justify-start text-sidebar-muted hover:bg-white/10 hover:text-sidebar-foreground">
            Cerrar sesión
          </Button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <div className="mx-auto w-full max-w-7xl px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
