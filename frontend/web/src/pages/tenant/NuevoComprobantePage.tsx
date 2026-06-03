import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { v4 as uuidv4 } from "uuid";
import { apiClient } from "@/lib/api-client";
import { getApiErrorMessage } from "@/lib/api-errors";
import { formatCurrency, roundCurrency } from "@/lib/format";
import { hasErrors, positiveNumber, required, type FieldErrors } from "@/lib/validation";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Field, Input, Select } from "@/components/ui/Form";
import { useToast } from "@/components/ui/Toast";
import type {
  CreateComprobanteRequest,
  DatosFactura,
  DetalleFactura,
  SriConfig,
  TipoIdentificacionComprador,
} from "@codelabs-billing/shared";

type DetalleInput = Pick<DetalleFactura, "codigo_principal" | "descripcion" | "cantidad" | "precio_unitario">;
type FormField = "identificacion_comprador" | "razon_social_comprador" | "fecha_emision" | "detalles";

const initialDetalle: DetalleInput = {
  codigo_principal: "001",
  descripcion: "",
  cantidad: 1,
  precio_unitario: 0,
};

export function NuevoComprobantePage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [errors, setErrors] = useState<FieldErrors<FormField>>({});

  const { data: sriConfig } = useQuery<SriConfig>({
    queryKey: ["config-sri"],
    queryFn: () => apiClient.get<SriConfig>("/config/sri").then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });
  const ivaVigente = sriConfig?.iva_vigente ?? { codigo_porcentaje: "4", tarifa: 15, descripcion: "IVA 15%" };

  const [receptor, setReceptor] = useState({
    tipo_identificacion_comprador: "05" as TipoIdentificacionComprador,
    identificacion_comprador: "",
    razon_social_comprador: "",
    email_comprador: "",
  });
  const [cabecera, setCabecera] = useState({
    establecimiento: "001",
    punto_emision: "001",
    fecha_emision: new Date().toLocaleDateString("es-EC"),
    direccion_establecimiento: "",
  });
  const [detalles, setDetalles] = useState<DetalleInput[]>([initialDetalle]);
  const [error, setError] = useState("");

  const calcularTotal = () => {
    const subtotal = detalles.reduce((acc, detalle) => acc + detalle.cantidad * detalle.precio_unitario, 0);
    const tasaIva = (ivaVigente.tarifa ?? 15) / 100;
    const iva = roundCurrency(subtotal * tasaIva);
    return { subtotal: roundCurrency(subtotal), iva, total: roundCurrency(subtotal + iva) };
  };

  const mutation = useMutation({
    mutationFn: (payload: CreateComprobanteRequest) => apiClient.post<{ id: string }>("/comprobantes", payload).then((r) => r.data),
    onSuccess: (data) => {
      toast.success("Factura enviada a procesamiento");
      navigate(`/comprobantes/${data.id}`);
    },
    onError: (err: unknown) => {
      const message = getApiErrorMessage(err, "Error al emitir");
      setError(message);
      toast.error(message);
    },
  });

  const validate = (): FieldErrors<FormField> => {
    const firstInvalidDetail = detalles.find((detalle) => {
      return required(detalle.codigo_principal, "Código") || required(detalle.descripcion, "Descripción") || positiveNumber(detalle.cantidad, "Cantidad") || positiveNumber(detalle.precio_unitario, "Precio unitario");
    });

    return {
      identificacion_comprador: required(receptor.identificacion_comprador, "Identificación"),
      razon_social_comprador: required(receptor.razon_social_comprador, "Razón social"),
      fecha_emision: required(cabecera.fecha_emision, "Fecha de emisión"),
      detalles: firstInvalidDetail ? "Cada línea debe tener código, descripción, cantidad y precio válidos" : undefined,
    };
  };

  const handleSubmit = () => {
    setError("");
    const nextErrors = validate();
    setErrors(nextErrors);
    if (hasErrors(nextErrors)) return;

    const { subtotal, total } = calcularTotal();
    const tasaIva = (ivaVigente.tarifa ?? 15) / 100;
    const detallesSRI: DetalleFactura[] = detalles.map((detalle) => {
      const base = roundCurrency(detalle.cantidad * detalle.precio_unitario);
      return {
        codigo_principal: detalle.codigo_principal,
        descripcion: detalle.descripcion,
        cantidad: detalle.cantidad,
        precio_unitario: detalle.precio_unitario,
        descuento: 0,
        precio_total_sin_impuesto: base,
        impuestos: [
          {
            codigo: "2",
            codigo_porcentaje: ivaVigente.codigo_porcentaje,
            tarifa: ivaVigente.tarifa,
            base_imponible: base,
            valor: roundCurrency(base * tasaIva),
          },
        ],
      };
    });

    const datos: DatosFactura = {
      ...receptor,
      email_comprador: receptor.email_comprador || null,
      fecha_emision: cabecera.fecha_emision,
      obligado_contabilidad: "NO",
      direccion_establecimiento: cabecera.direccion_establecimiento,
      detalles: detallesSRI,
      total_sin_impuestos: subtotal,
      total_descuento: 0,
      importe_total: total,
      pagos: [{ forma_pago: "01", total, plazo: 0, unidad_tiempo: "dias" }],
    };

    mutation.mutate({
      tipo: "01",
      establecimiento: cabecera.establecimiento,
      punto_emision: cabecera.punto_emision,
      idempotency_key: uuidv4(),
      datos,
    });
  };

  const updateDetalle = (index: number, patch: Partial<DetalleInput>) => {
    setDetalles((current) => current.map((detalle, itemIndex) => (itemIndex === index ? { ...detalle, ...patch } : detalle)));
  };

  const { subtotal, iva, total } = calcularTotal();

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-brand">Emisión</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight">Nueva factura</h1>
      </div>

      <Card>
        <CardContent className="space-y-3">
          <h2 className="text-sm font-semibold">Emisión</h2>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Establecimiento">
              <Input value={cabecera.establecimiento} maxLength={3} onChange={(event) => setCabecera({ ...cabecera, establecimiento: event.target.value.replace(/\D/g, "") })} />
            </Field>
            <Field label="Punto emisión">
              <Input value={cabecera.punto_emision} maxLength={3} onChange={(event) => setCabecera({ ...cabecera, punto_emision: event.target.value.replace(/\D/g, "") })} />
            </Field>
            <Field label="Fecha emisión" error={errors.fecha_emision}>
              <Input value={cabecera.fecha_emision} hasError={!!errors.fecha_emision} onChange={(event) => setCabecera({ ...cabecera, fecha_emision: event.target.value })} />
            </Field>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-3">
          <h2 className="text-sm font-semibold">Receptor</h2>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Tipo identificación">
              <Select value={receptor.tipo_identificacion_comprador} onChange={(event) => setReceptor({ ...receptor, tipo_identificacion_comprador: event.target.value as TipoIdentificacionComprador })}>
                <option value="04">RUC</option>
                <option value="05">Cédula</option>
                <option value="06">Pasaporte</option>
                <option value="07">Consumidor final</option>
              </Select>
            </Field>
            <Field label="Identificación" error={errors.identificacion_comprador}>
              <Input value={receptor.identificacion_comprador} hasError={!!errors.identificacion_comprador} onChange={(event) => setReceptor({ ...receptor, identificacion_comprador: event.target.value })} />
            </Field>
            <Field label="Razón social" error={errors.razon_social_comprador}>
              <Input value={receptor.razon_social_comprador} hasError={!!errors.razon_social_comprador} onChange={(event) => setReceptor({ ...receptor, razon_social_comprador: event.target.value })} />
            </Field>
            <Field label="Email">
              <Input type="email" value={receptor.email_comprador} onChange={(event) => setReceptor({ ...receptor, email_comprador: event.target.value })} />
            </Field>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Detalles</h2>
            <Button variant="outline" size="sm" onClick={() => setDetalles([...detalles, { ...initialDetalle, codigo_principal: "" }])}>
              Agregar línea
            </Button>
          </div>
          {errors.detalles && <Alert tone="danger">{errors.detalles}</Alert>}
          {detalles.map((detalle, index) => (
            <div key={index} className="grid grid-cols-12 items-end gap-2">
              <Field label="Código" className="col-span-2">
                <Input className="text-xs" value={detalle.codigo_principal} onChange={(event) => updateDetalle(index, { codigo_principal: event.target.value })} />
              </Field>
              <Field label="Descripción" className="col-span-4">
                <Input className="text-xs" value={detalle.descripcion} onChange={(event) => updateDetalle(index, { descripcion: event.target.value })} />
              </Field>
              <Field label="Cantidad" className="col-span-2">
                <Input type="number" className="text-xs" value={detalle.cantidad} onChange={(event) => updateDetalle(index, { cantidad: Number(event.target.value) })} />
              </Field>
              <Field label="P. unitario" className="col-span-2">
                <Input type="number" step="0.01" className="text-xs" value={detalle.precio_unitario} onChange={(event) => updateDetalle(index, { precio_unitario: Number(event.target.value) })} />
              </Field>
              <p className="col-span-1 pb-2 font-mono text-xs">{formatCurrency(detalle.cantidad * detalle.precio_unitario)}</p>
              <div className="col-span-1 pb-1">
                {detalles.length > 1 && (
                  <Button variant="ghost" size="sm" onClick={() => setDetalles(detalles.filter((_, itemIndex) => itemIndex !== index))}>
                    Quitar
                  </Button>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <div className="min-w-[220px] space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Subtotal:</span>
            <span>{formatCurrency(subtotal)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">IVA {ivaVigente.tarifa}%:</span>
            <span>{formatCurrency(iva)}</span>
          </div>
          <div className="flex justify-between border-t pt-1 font-bold">
            <span>Total:</span>
            <span>{formatCurrency(total)}</span>
          </div>
        </div>
      </div>

      {error && <Alert tone="danger">{error}</Alert>}

      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={() => navigate(-1)}>
          Cancelar
        </Button>
        <Button onClick={handleSubmit} isLoading={mutation.isPending}>
          Emitir factura
        </Button>
      </div>
    </div>
  );
}
