import { useState } from "react";
import { CertificateUploadForm } from "@/components/certificates/CertificateUploadForm";
import { SriConfigTab } from "@/components/configuracion/SriConfigTab";
import { EmpresaConfigTab } from "@/components/configuracion/EmpresaConfigTab";
import { Tabs, type TabItem } from "@/components/ui/Tabs";

type Tab = "empresa" | "firma" | "sri";

export function ConfiguracionPage() {
  const [activeTab, setActiveTab] = useState<Tab>("empresa");

  const TABS: TabItem<Tab>[] = [
    { id: "empresa", label: "Empresa" },
    { id: "firma", label: "Firma electrónica" },
    { id: "sri", label: "Configuración SRI" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-brand">Administración</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight">Configuración</h1>
      </div>
      <Tabs items={TABS} active={activeTab} onChange={setActiveTab} />
      {activeTab === "empresa" && <EmpresaConfigTab />}
      {activeTab === "firma" && <CertificateUploadForm />}
      {activeTab === "sri" && <SriConfigTab />}
    </div>
  );
}
