import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { v4 as uuidv4 } from "uuid";

interface SriConfig {
  iva_vigente: { codigo_porcentaje: string; tarifa: number };
}

interface Detalle {
  codigo_principal: string;
  descripcion: string;
  cantidad: number;
  precio_unitario: number;
}

function round2(n: number) { return Math.round(n * 100) / 100; }

export function NuevoComprobantePage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const { data: sriConfig } = useQuery<SriConfig>({
    queryKey: ["config-sri"],
    queryFn: () => apiClient.get<SriConfig>("/config/sri").then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });
  const ivaVigente = sriConfig?.iva_vigente ?? { codigo_porcentaje: "4", tarifa: 15 };

  const [receptor, setReceptor] = useState({ tipo_identificacion_comprador: "05", identificacion_comprador: "", razon_social_comprador: "", email_comprador: "" });
  const [cabecera, setCabecera] = useState({ establecimiento: "001", punto_emision: "001", fecha_emision: new Date().toLocaleDateString("es-EC"), obligado_contabilidad: "NO", direccion_establecimiento: "" });
  const [detalles, setDetalles] = useState<Detalle[]>([{ codigo_principal: "001", descripcion: "", cantidad: 1, precio_unitario: 0 }]);
  const [error, setError] = useState("");

  const calcularTotal = () => {
    const subtotal = detalles.reduce((acc, d) => acc + d.cantidad * d.precio_unitario, 0);
    const tasaIva = (ivaVigente.tarifa ?? 15) / 100;
    const iva = round2(subtotal * tasaIva);
    return { subtotal: round2(subtotal), iva, total: round2(subtotal + iva) };
  };

  const mutation = useMutation({
    mutationFn: (payload: unknown) => apiClient.post<{ id: string }>("/comprobantes", payload).then((r) => r.data),
    onSuccess: (data) => navigate(`/comprobantes/${data.id}`),
    onError: (err: any) => setError(err.response?.data?.detail?.message ?? "Error al emitir"),
  });

  const handleSubmit = () => {
    setError("");
    const { subtotal, iva, total } = calcularTotal();
    const tasaIva = (ivaVigente.tarifa ?? 15) / 100;
    const detallesSRI = detalles.map((d) => {
      const base = round2(d.cantidad * d.precio_unitario);
      return {
        codigo_principal: d.codigo_principal,
        descripcion: d.descripcion,
        cantidad: d.cantidad,
        precio_unitario: d.precio_unitario,
        descuento: 0,
        precio_total_sin_impuesto: base,
        impuestos: [{ codigo: "2", codigo_porcentaje: ivaVigente.codigo_porcentaje, tarifa: ivaVigente.tarifa, base_imponible: base, valor: round2(base * tasaIva) }],
      };
    });
    mutation.mutate({
      tipo: "01",
      establecimiento: cabecera.establecimiento,
      punto_emision: cabecera.punto_emision,
      idempotency_key: uuidv4(),
      datos: { ...receptor, fecha_emision: cabecera.fecha_emision, obligado_contabilidad: cabecera.obligado_contabilidad, direccion_establecimiento: cabecera.direccion_establecimiento, detalles: detallesSRI, total_sin_impuestos: subtotal, total_descuento: 0, importe_total: total, pagos: [{ forma_pago: "01", total, plazo: 0, unidad_tiempo: "dias" }] },
    });
  };

  const { subtotal, iva, total } = calcularTotal();

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">Nueva factura</h1>

      <section className="rounded-lg border border-border p-4 space-y-3">
        <h2 className="font-semibold text-sm">Emisión</h2>
        <div className="grid grid-cols-3 gap-3">
          {(["establecimiento", "punto_emision", "fecha_emision"] as const).map((k) => (
            <div key={k}>
              <label className="text-xs font-medium capitalize">{k.replace(/_/g, " ")}</label>
              <input className="mt-1 w-full rounded border border-input bg-background px-2 py-1 text-sm" value={cabecera[k]} onChange={(e) => setCabecera({ ...cabecera, [k]: e.target.value })} />
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-border p-4 space-y-3">
        <h2 className="font-semibold text-sm">Receptor</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium">Tipo identificación</label>
            <select className="mt-1 w-full rounded border border-input bg-background px-2 py-1 text-sm" value={receptor.tipo_identificacion_comprador} onChange={(e) => setReceptor({ ...receptor, tipo_identificacion_comprador: e.target.value })}>
              <option value="04">RUC</option>
              <option value="05">Cédula</option>
              <option value="06">Pasaporte</option>
              <option value="07">Consumidor final</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium">Identificación</label>
            <input className="mt-1 w-full rounded border border-input bg-background px-2 py-1 text-sm" value={receptor.identificacion_comprador} onChange={(e) => setReceptor({ ...receptor, identificacion_comprador: e.target.value })} />
          </div>
          <div>
            <label className="text-xs font-medium">Razón social</label>
            <input className="mt-1 w-full rounded border border-input bg-background px-2 py-1 text-sm" value={receptor.razon_social_comprador} onChange={(e) => setReceptor({ ...receptor, razon_social_comprador: e.target.value })} />
          </div>
          <div>
            <label className="text-xs font-medium">Email</label>
            <input type="email" className="mt-1 w-full rounded border border-input bg-background px-2 py-1 text-sm" value={receptor.email_comprador} onChange={(e) => setReceptor({ ...receptor, email_comprador: e.target.value })} />
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-border p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-sm">Detalles</h2>
          <button onClick={() => setDetalles([...detalles, { codigo_principal: "", descripcion: "", cantidad: 1, precio_unitario: 0 }])} className="text-xs text-primary hover:underline">+ Agregar línea</button>
        </div>
        {detalles.map((det, i) => (
          <div key={i} className="grid grid-cols-12 gap-2 items-end">
            <div className="col-span-2"><label className="text-xs text-muted-foreground">Código</label><input className="mt-0.5 w-full rounded border border-input bg-background px-2 py-1 text-xs" value={det.codigo_principal} onChange={(e) => { const d = [...detalles]; d[i].codigo_principal = e.target.value; setDetalles(d); }} /></div>
            <div className="col-span-4"><label className="text-xs text-muted-foreground">Descripción</label><input className="mt-0.5 w-full rounded border border-input bg-background px-2 py-1 text-xs" value={det.descripcion} onChange={(e) => { const d = [...detalles]; d[i].descripcion = e.target.value; setDetalles(d); }} /></div>
            <div className="col-span-2"><label className="text-xs text-muted-foreground">Cantidad</label><input type="number" className="mt-0.5 w-full rounded border border-input bg-background px-2 py-1 text-xs" value={det.cantidad} onChange={(e) => { const d = [...detalles]; d[i].cantidad = +e.target.value; setDetalles(d); }} /></div>
            <div className="col-span-2"><label className="text-xs text-muted-foreground">P. unitario</label><input type="number" step="0.01" className="mt-0.5 w-full rounded border border-input bg-background px-2 py-1 text-xs" value={det.precio_unitario} onChange={(e) => { const d = [...detalles]; d[i].precio_unitario = +e.target.value; setDetalles(d); }} /></div>
            <div className="col-span-1"><p className="text-xs font-mono mt-0.5">${round2(det.cantidad * det.precio_unitario).toFixed(2)}</p></div>
            <div className="col-span-1">{detalles.length > 1 && <button onClick={() => setDetalles(detalles.filter((_, j) => j !== i))} className="text-xs text-destructive">×</button>}</div>
          </div>
        ))}
      </section>

      <div className="flex justify-end">
        <div className="space-y-1 text-sm min-w-[200px]">
          <div className="flex justify-between"><span className="text-muted-foreground">Subtotal:</span><span>${subtotal.toFixed(2)}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">IVA {ivaVigente.tarifa}%:</span><span>${iva.toFixed(2)}</span></div>
          <div className="flex justify-between font-bold border-t pt-1"><span>Total:</span><span>${total.toFixed(2)}</span></div>
        </div>
      </div>

      {error && <div className="rounded-md bg-destructive/10 border border-destructive/30 px-3 py-2 text-sm text-destructive">{error}</div>}

      <div className="flex gap-3 justify-end">
        <button onClick={() => navigate(-1)} className="rounded-md border border-input px-4 py-2 text-sm hover:bg-muted">Cancelar</button>
        <button onClick={handleSubmit} disabled={mutation.isPending} className="rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50">{mutation.isPending ? "Emitiendo..." : "Emitir factura"}</button>
      </div>
    </div>
  );
}
