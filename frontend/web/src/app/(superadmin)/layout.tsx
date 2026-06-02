import { redirect } from "next/navigation";

export default function SuperadminLayout({ children }: { children: React.ReactNode }) {
  // TODO Fase 2: verificar que el usuario es superadmin desde el JWT
  // Por ahora el guard se aplica en cada page via server component
  return (
    <div className="flex min-h-screen">
      <aside className="w-64 border-r border-border bg-card p-4">
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Superadmin
          </h2>
        </div>
        <nav className="space-y-1">
          <a href="/tenants" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent">
            Tenants
          </a>
          <a href="/planes" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent">
            Planes
          </a>
          <a href="/sistema" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent">
            Sistema
          </a>
        </nav>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
