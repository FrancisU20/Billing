"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";

export default function SuperadminLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && (!user || !user.isSuperadmin)) {
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

  if (!user?.isSuperadmin) return null;

  return (
    <div className="flex min-h-screen">
      <aside className="w-64 border-r border-border bg-card flex flex-col">
        <div className="p-4 border-b border-border">
          <p className="text-xs font-bold text-primary">CodeLabs Billing</p>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mt-1">
            Superadmin
          </p>
        </div>
        <nav className="flex-1 p-3 space-y-0.5">
          {[
            { href: "/tenants", label: "Tenants" },
            { href: "/planes", label: "Planes" },
            { href: "/sistema", label: "Sistema" },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"
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
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
