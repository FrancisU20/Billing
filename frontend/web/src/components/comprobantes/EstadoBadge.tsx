import type { EstadoComprobante } from "@codelabs-billing/shared";

const COLORES: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  PENDING_VALIDATION: "bg-blue-100 text-blue-700",
  VALIDATION_FAILED: "bg-red-100 text-red-700",
  QUEUED: "bg-yellow-100 text-yellow-700",
  PROCESSING: "bg-yellow-100 text-yellow-700",
  XML_GENERATED: "bg-blue-100 text-blue-600",
  XML_SIGNED: "bg-blue-100 text-blue-600",
  SENT_TO_SRI: "bg-indigo-100 text-indigo-700",
  RECEIVED_BY_SRI: "bg-indigo-100 text-indigo-700",
  RETURNED_BY_SRI: "bg-orange-100 text-orange-700",
  PENDING_AUTHORIZATION: "bg-purple-100 text-purple-700",
  AUTHORIZED: "bg-green-100 text-green-700",
  NOT_AUTHORIZED: "bg-red-100 text-red-700",
  EMAIL_PENDING: "bg-teal-100 text-teal-700",
  EMAIL_SENT: "bg-green-100 text-green-600",
  EMAIL_FAILED: "bg-orange-100 text-orange-700",
  FAILED: "bg-red-100 text-red-700",
  RETRY_PENDING: "bg-yellow-100 text-yellow-600",
  MANUAL_REVIEW_REQUIRED: "bg-red-200 text-red-800",
  CANCELLED: "bg-gray-100 text-gray-500",
};

export function EstadoBadge({ estado }: { estado: EstadoComprobante | string }) {
  const color = COLORES[estado] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>
      {estado.replace(/_/g, " ")}
    </span>
  );
}
