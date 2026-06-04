"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { getApiErrorMessage } from "@/lib/api-errors";
import {
  listCertificates,
  uploadAndValidateCertificate,
  type CertificateUploadPhase,
} from "@/lib/certificates";
import { certificateTone } from "@/lib/status-styles";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Form";
import { useToast } from "@/components/ui/Toast";
import type { Certificate } from "@codelabs-billing/shared";

type UploadStep = "idle" | CertificateUploadPhase | "done" | "error";

function isBusyStep(step: UploadStep): step is CertificateUploadPhase {
  return step === "requesting-url" || step === "uploading-file" || step === "validating-certificate";
}

function uploadButtonText(step: UploadStep) {
  if (step === "requesting-url") return "Preparando carga";
  if (step === "uploading-file") return "Subiendo certificado";
  if (step === "validating-certificate") return "Validando firma";
  return "Subir y validar firma";
}

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
  const [fileInputKey, setFileInputKey] = useState(0);

  const { data: certificates = [] } = useQuery<Certificate[]>({
    queryKey: ["certificates", tenantId],
    queryFn: () => listCertificates(tenantId),
    enabled: !!tenantId,
  });

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!tenantId || !file || !password) {
        throw new Error("Selecciona el archivo y escribe la contraseña del certificado");
      }

      setErrorMsg("");
      return uploadAndValidateCertificate({
        tenantId,
        file,
        password,
        nombre,
        onPhaseChange: setStep,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["certificates"] });
      setStep("done");
      setFile(null);
      setPassword("");
      setNombre("");
      setFileInputKey((value) => value + 1);
      toast.success("Certificado cargado y validado correctamente");
    },
    onError: (err: unknown) => {
      setStep("error");
      const message = getApiErrorMessage(err, "No se pudo cargar y validar el certificado");
      setErrorMsg(message);
      toast.error(message);
    },
  });
  const isBusy = uploadMutation.isPending || isBusyStep(step);

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
            onClick={() => {
              setStep("idle");
              setErrorMsg("");
            }}
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
                disabled={isBusy}
              />
            </Field>

            <Field label="Archivo .p12 *">
              <Input
                key={fileInputKey}
                type="file"
                accept=".p12,.pfx"
                className="h-auto file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary-foreground"
                disabled={isBusy}
                onChange={(e) => {
                  const selected = e.target.files?.[0] ?? null;
                  setStep("idle");
                  setErrorMsg("");
                  if (selected && !/\.(p12|pfx)$/i.test(selected.name)) {
                    setErrorMsg("El archivo debe tener extensión .p12 o .pfx");
                    e.target.value = "";
                    setFile(null);
                    return;
                  }
                  if (selected && selected.size > 5 * 1024 * 1024) {
                    setErrorMsg("El archivo no puede superar 5 MB");
                    e.target.value = "";
                    setFile(null);
                    return;
                  }
                  setFile(selected);
                }}
              />
            </Field>

            <Field
              label="Contraseña del certificado *"
              hint="La contraseña se cifra con KMS y se guarda en AWS Secrets Manager, nunca en texto plano."
            >
              <Input
                type="password"
                placeholder="Contraseña del .p12"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isBusy}
              />
            </Field>

            {errorMsg && (
              <Alert tone="danger">{errorMsg}</Alert>
            )}

            <div className="flex gap-3 justify-end">
              <Button
                onClick={() => uploadMutation.mutate()}
                disabled={!file || !password || isBusy}
                isLoading={isBusy}
              >
                {uploadButtonText(step)}
              </Button>
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
