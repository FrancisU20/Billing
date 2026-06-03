import { useState } from "react";
import { CertificateUploadForm } from "@/components/certificates/CertificateUploadForm";
import { SriConfigTab } from "@/components/configuracion/SriConfigTab";
import { EmpresaConfigTab } from "@/components/configuracion/EmpresaConfigTab";

type Tab = "empresa" | "firma" | "sri";

export function ConfiguracionPage() {
  const [activeTab, setActiveTab] = useState<Tab>("empresa");

  const TABS: { id: Tab; label: string }[] = [
    { id: "empresa", label: "Empresa" },
    { id: "firma", label: "Firma electrónica" },
    { id: "sri", label: "Configuración SRI" },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Configuración</h1>
      <div className="flex gap-1 border-b border-border">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === id ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {activeTab === "empresa" && <EmpresaConfigTab />}
      {activeTab === "firma" && <CertificateUploadForm />}
      {activeTab === "sri" && <SriConfigTab />}
    </div>
  );
}
