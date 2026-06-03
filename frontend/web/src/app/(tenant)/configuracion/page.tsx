"use client";

import { useState } from "react";
import { CertificateUploadForm } from "@/components/certificates/CertificateUploadForm";
import { SriConfigTab } from "@/components/configuracion/SriConfigTab";
import { EmpresaConfigTab } from "@/components/configuracion/EmpresaConfigTab";

export default function ConfiguracionPage() {
  const [activeTab, setActiveTab] = useState<"empresa" | "firma" | "sri">("empresa");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Configuración</h1>

      <div className="flex gap-1 border-b border-border">
        {(["empresa", "firma", "sri"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              activeTab === tab
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab === "firma" ? "Firma electrónica" : tab === "sri" ? "Configuración SRI" : "Empresa"}
          </button>
        ))}
      </div>

      {activeTab === "empresa" && <EmpresaConfigTab />}
      {activeTab === "firma" && <CertificateUploadForm />}
      {activeTab === "sri" && <SriConfigTab />}
    </div>
  );
}
