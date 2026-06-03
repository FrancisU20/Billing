export function roundCurrency(value: number) {
  return Math.round(value * 100) / 100;
}

export function formatCurrency(value: number) {
  return `$${roundCurrency(value).toFixed(2)}`;
}

export function formatComprobanteNumber(
  establecimiento: string,
  puntoEmision: string,
  secuencial: string | null
) {
  return `${establecimiento}-${puntoEmision}-${secuencial?.padStart(9, "0") ?? "---------"}`;
}
