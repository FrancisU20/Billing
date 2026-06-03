export default function TenantLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 border-r border-border bg-card p-4">
        <div className="mb-6">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Panel</p>
        </div>
        <nav className="space-y-1">
          {[
            { href: "/dashboard", label: "Dashboard" },
            { href: "/comprobantes", label: "Comprobantes" },
            { href: "/lotes", label: "Carga masiva" },
            { href: "/reportes", label: "Reportes" },
            { href: "/configuracion", label: "Configuración" },
          ].map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="flex items-center rounded-md px-3 py-2 text-sm hover:bg-accent"
            >
              {item.label}
            </a>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
