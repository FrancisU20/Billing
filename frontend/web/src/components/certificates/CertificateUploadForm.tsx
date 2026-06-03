"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

type UploadStep = "idle" | "uploading" | "confirming" | "done" | "error";

interface CertificateInfo {
  id: string;
  nombre: string | null;
  fecha_emision: string | null;
  fecha_expiracion: string | null;
  estado: string;
}

export function CertificateUploadForm() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const tenantId = user?.tenantId ?? "";

  const [step, setStep] = useState<UploadStep>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [certId, setCertId] = useState("");
  const [s3KeyUpload, setS3KeyUpload] = useState("");
  const { data: certificates = [] } = useQuery<CertificateInfo[]>({
    queryKey: ["certificates", tenantId],
    queryFn: () => apiClient.get<CertificateInfo[]>(`/tenants/${tenantId}/certificates`).then((r) => r.data),
    enabled: !!tenantId,
  });

  const handleUpload = async () => {
    if (!file || !password) return;
    setStep("uploading");
    setErrorMsg("");

    try {
      // Paso 1: Solicitar presigned URL
      const { data } = await apiClient.post(`/tenants/${tenantId}/certificates/upload-url`);
      setCertId(data.cert_id);

      // Paso 2: Subir .p12 directamente a S3 — NUNCA pasa por el backend
      await fetch(data.upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": "application/x-pkcs12" },
      });

      // La clave de S3 se deriva del cert_id — el backend la calcula igual
      setS3KeyUpload(`tenants/${tenantId}/certs/uploads/${data.cert_id}.p12`);
      setStep("confirming");
    } catch {
      setStep("error");
      setErrorMsg("Error al subir el certificado. Intenta de nuevo.");
    }
  };

  const confirmMutation = useMutation({
    mutationFn: () =>
      apiClient.post(`/tenants/${tenantId}/certificates/confirm`, {
        cert_id: certId,
        s3_key_upload: s3KeyUpload,
        password,
        nombre: nombre || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["certificates"] });
      setStep("done");
      setFile(null);
      setPassword("");
      setNombre("");
    },
    onError: (err: any) => {
      setStep("error");
      setErrorMsg(err.response?.data?.detail ?? "Contraseña incorrecta o certificado inválido");
    },
  });

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h2 className="font-semibold">Firma electrónica</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Carga el archivo .p12 emitido por el BCE u otro proveedor autorizado.
          El archivo se almacena cifrado — la contraseña nunca se guarda en texto plano.
        </p>
      </div>

      {/* Certificados existentes */}
      {certificates.length > 0 && (
        <div className="rounded-lg border border-border divide-y divide-border">
          {certificates.map((cert) => (
            <div key={cert.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="text-sm font-medium">{cert.nombre ?? "Certificado sin nombre"}</p>
                <p className="text-xs text-muted-foreground">
                  Vence: {cert.fecha_expiracion ?? "—"}
                </p>
              </div>
              <CertEstadoBadge estado={cert.estado} />
            </div>
          ))}
        </div>
      )}

      {/* Formulario de carga */}
      {step === "done" ? (
        <div className="rounded-lg bg-green-50 border border-green-200 p-4 text-sm text-green-700">
          ✓ Certificado cargado y validado correctamente.
          <button
            onClick={() => setStep("idle")}
            className="ml-4 underline text-green-800"
          >
            Cargar otro
          </button>
        </div>
      ) : (
        <div className="rounded-lg border border-border p-4 space-y-4">
          <h3 className="text-sm font-medium">Cargar nuevo certificado</h3>

          <div>
            <label className="text-sm font-medium">Nombre (opcional)</label>
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Ej. Certificado BCE 2024"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
            />
          </div>

          <div>
            <label className="text-sm font-medium">Archivo .p12 *</label>
            <input
              type="file"
              accept=".p12,.pfx"
              className="mt-1 w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary-foreground"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>

          <div>
            <label className="text-sm font-medium">Contraseña del certificado *</label>
            <input
              type="password"
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Contraseña del .p12"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              La contraseña se cifra con KMS y se guarda en AWS Secrets Manager — nunca en texto plano.
            </p>
          </div>

          {errorMsg && (
            <div className="rounded-md bg-destructive/10 border border-destructive/30 px-3 py-2 text-sm text-destructive">
              {errorMsg}
            </div>
          )}

          <div className="flex gap-3 justify-end">
            {step === "confirming" ? (
              <button
                onClick={() => confirmMutation.mutate()}
                disabled={confirmMutation.isPending}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
              >
                {confirmMutation.isPending ? "Validando..." : "Confirmar carga"}
              </button>
            ) : (
              <button
                onClick={handleUpload}
                disabled={!file || !password || step === "uploading"}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
              >
                {step === "uploading" ? "Subiendo..." : "Subir certificado"}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function CertEstadoBadge({ estado }: { estado: string }) {
  const colors: Record<string, string> = {
    ACTIVE: "bg-green-100 text-green-700",
    EXPIRED: "bg-red-100 text-red-700",
    REVOKED: "bg-gray-100 text-gray-600",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[estado] ?? "bg-gray-100 text-gray-600"}`}>
      {estado}
    </span>
  );
}
