"use client";

import { useState } from "react";
import { CertificateUploadForm } from "@/components/certificates/CertificateUploadForm";

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

      {activeTab === "empresa" && <EmpresaTab />}
      {activeTab === "firma" && <CertificateUploadForm />}
      {activeTab === "sri" && <SriTab />}
    </div>
  );
}

function EmpresaTab() {
  return (
    <div className="max-w-lg space-y-4">
      <p className="text-sm text-muted-foreground">
        Configura los datos de tu empresa que aparecerán en los comprobantes.
      </p>
      {/* TODO Fase 2: formulario con logo, colores y datos comerciales */}
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-muted-foreground text-sm">
        Configuración de empresa — implementar con formulario completo
      </div>
    </div>
  );
}

function SriTab() {
  return (
    <div className="max-w-lg space-y-4">
      <p className="text-sm text-muted-foreground">
        Configura los establecimientos y puntos de emisión ante el SRI.
      </p>
      {/* TODO Fase 2: formulario de establecimientos, puntos de emisión y secuenciales */}
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-muted-foreground text-sm">
        Configuración SRI — implementar en Fase 2
      </div>
    </div>
  );
}
