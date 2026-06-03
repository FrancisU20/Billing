"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { getApiErrorMessage } from "@/lib/api-errors";
import { certificateTone } from "@/lib/status-styles";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Form";
import { useToast } from "@/components/ui/Toast";
import type {
  Certificate,
  ConfirmCertificateRequest,
  UploadCertificateUrlResponse,
} from "@codelabs-billing/shared";

type UploadStep = "idle" | "uploading" | "confirming" | "done" | "error";

export function CertificateUploadForm() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { user } = useAuth();
  const tenantId = user?.tenantId ?? "";

  const [step, setStep] = useState<UploadStep>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [certId, setCertId] = useState("");
  const [s3KeyUpload, setS3KeyUpload] = useState("");
  const { data: certificates = [] } = useQuery<Certificate[]>({
    queryKey: ["certificates", tenantId],
    queryFn: () => apiClient.get<Certificate[]>(`/tenants/${tenantId}/certificates`).then((r) => r.data),
    enabled: !!tenantId,
  });

  const handleUpload = async () => {
    if (!file || !password) return;
    setStep("uploading");
    setErrorMsg("");

    try {
      // Paso 1: Solicitar presigned URL
      const { data } = await apiClient.post<UploadCertificateUrlResponse>(`/tenants/${tenantId}/certificates/upload-url`);
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
      const message = "Error al subir el certificado. Intenta de nuevo.";
      setErrorMsg(message);
      toast.error(message);
    }
  };

  const confirmMutation = useMutation({
    mutationFn: () => {
      const payload: ConfirmCertificateRequest = {
        cert_id: certId,
        s3_key_upload: s3KeyUpload,
        password,
        nombre: nombre || null,
      };
      return apiClient.post(`/tenants/${tenantId}/certificates/confirm`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["certificates"] });
      setStep("done");
      setFile(null);
      setPassword("");
      setNombre("");
      toast.success("Certificado cargado y validado correctamente");
    },
    onError: (err: unknown) => {
      setStep("error");
      const message = getApiErrorMessage(err, "Contraseña incorrecta o certificado inválido");
      setErrorMsg(message);
      toast.error(message);
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
        <Card className="divide-y divide-border">
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
        </Card>
      )}

      {/* Formulario de carga */}
      {step === "done" ? (
        <Alert tone="success">
          Certificado cargado y validado correctamente.
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setStep("idle")}
            className="ml-2 h-6 px-2"
          >
            Cargar otro
          </Button>
        </Alert>
      ) : (
        <Card>
          <CardContent className="space-y-4">
          <h3 className="text-sm font-medium">Cargar nuevo certificado</h3>

          <Field label="Nombre (opcional)">
            <Input
              placeholder="Ej. Certificado BCE 2024"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
            />
          </Field>

          <Field label="Archivo .p12 *">
            <Input
              type="file"
              accept=".p12,.pfx"
              className="h-auto file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary-foreground"
              onChange={(e) => {
                const selected = e.target.files?.[0] ?? null;
                if (selected && !/\.(p12|pfx)$/i.test(selected.name)) {
                  setErrorMsg("El archivo debe tener extensión .p12 o .pfx");
                  e.target.value = "";
                  return;
                }
                if (selected && selected.size > 5 * 1024 * 1024) {
                  setErrorMsg("El archivo no puede superar 5 MB");
                  e.target.value = "";
                  return;
                }
                setFile(selected);
              }}
            />
          </Field>

          <Field label="Contraseña del certificado *" hint="La contraseña se cifra con KMS y se guarda en AWS Secrets Manager, nunca en texto plano.">
            <Input
              type="password"
              placeholder="Contraseña del .p12"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>

          {errorMsg && (
            <Alert tone="danger">{errorMsg}</Alert>
          )}

          <div className="flex gap-3 justify-end">
            {step === "confirming" ? (
              <Button
                onClick={() => confirmMutation.mutate()}
                isLoading={confirmMutation.isPending}
              >
                Confirmar carga
              </Button>
            ) : (
              <Button
                onClick={handleUpload}
                disabled={!file || !password || step === "uploading"}
                isLoading={step === "uploading"}
              >
                Subir certificado
              </Button>
            )}
          </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function CertEstadoBadge({ estado }: { estado: string }) {
  return <Badge tone={certificateTone(estado)}>{estado}</Badge>;
}
