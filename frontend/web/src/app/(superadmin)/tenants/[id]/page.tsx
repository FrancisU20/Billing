import TenantDetailClient from "./TenantDetailClient";

export function generateStaticParams() {
  return [{ id: "_" }];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function TenantDetailPage({ params }: any) {
  return <TenantDetailClient id={params.id as string} />;
}
