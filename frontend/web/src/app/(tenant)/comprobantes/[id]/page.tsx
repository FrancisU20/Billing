import ComprobanteDetalleClient from "./ComprobanteDetalleClient";

// Con output: 'export', Next.js requiere al menos un valor.
// El id '_' nunca se usa en producción — el CloudFront Function reescribe
// todos los paths a /index.html y React Router toma el control.
export function generateStaticParams() {
  return [{ id: "_" }];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function ComprobanteDetallePage({ params }: any) {
  return <ComprobanteDetalleClient id={params.id as string} />;
}
