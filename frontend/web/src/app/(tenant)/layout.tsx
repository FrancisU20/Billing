"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";

export default function TenantLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Cargando...</p>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 border-r border-border bg-card flex flex-col">
        <div className="p-4 border-b border-border">
          <p className="text-xs font-bold text-primary">CodeLabs Billing</p>
          <p className="text-xs text-muted-foreground truncate mt-0.5">{user.email}</p>
        </div>
        <nav className="flex-1 p-3 space-y-0.5">
          {[
            { href: "/dashboard", label: "Dashboard" },
            { href: "/comprobantes", label: "Comprobantes" },
            { href: "/lotes", label: "Carga masiva" },
            { href: "/reportes", label: "Reportes" },
            { href: "/configuracion", label: "Configuración" },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center rounded-md px-3 py-2 text-sm hover:bg-accent"
            >
              {item.label}
            </Link>
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
      <main className="flex-1 p-8 overflow-auto">{children}</main>
    </div>
  );
}
