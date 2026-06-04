import type {
  Certificate,
  ConfirmCertificateRequest,
  UploadCertificateUrlResponse,
} from "@codelabs-billing/shared";
import { apiClient } from "./api-client";

export type CertificateUploadPhase = "requesting-url" | "uploading-file" | "validating-certificate";

export type UploadAndValidateCertificateInput = {
  tenantId: string;
  file: File;
  password: string;
  nombre?: string | null;
  onPhaseChange?: (phase: CertificateUploadPhase) => void;
};

export async function listCertificates(tenantId: string) {
  const { data } = await apiClient.get<Certificate[]>(`/tenants/${tenantId}/certificates`);
  return data;
}

export async function uploadAndValidateCertificate({
  tenantId,
  file,
  password,
  nombre,
  onPhaseChange,
}: UploadAndValidateCertificateInput) {
  onPhaseChange?.("requesting-url");
  const { data: upload } = await apiClient.post<UploadCertificateUrlResponse>(
    `/tenants/${tenantId}/certificates/upload-url`
  );

  onPhaseChange?.("uploading-file");
  const uploadResponse = await fetch(upload.upload_url, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": "application/x-pkcs12" },
  });

  if (!uploadResponse.ok) {
    throw new Error("No se pudo subir el certificado al almacenamiento seguro");
  }

  onPhaseChange?.("validating-certificate");
  const payload: ConfirmCertificateRequest = {
    cert_id: upload.cert_id,
    password,
    nombre: nombre?.trim() || null,
  };
  const { data } = await apiClient.post<Certificate>(`/tenants/${tenantId}/certificates/confirm`, payload);
  return data;
}
