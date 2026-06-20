import { ECUADOR_TIME_ZONE, dateOnlyToLocalDate, isDateOnly } from './ecuador-time'

export function formatCurrency(amount: string | number, currency = 'USD'): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  return new Intl.NumberFormat('es-EC', { style: 'currency', currency }).format(num)
}

export function formatDate(iso: string): string {
  const value = isDateOnly(iso) ? dateOnlyToLocalDate(iso) : new Date(iso)
  return new Intl.DateTimeFormat('es-EC', {
    timeZone: isDateOnly(iso) ? undefined : ECUADOR_TIME_ZONE,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(value)
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('es-EC', {
    timeZone: ECUADOR_TIME_ZONE,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(new Date(iso))
}

export function formatDateRangeLabel(from: string, to: string): string {
  if (from && to) return `${from} – ${to}`
  if (from) return `Desde ${from}`
  return `Hasta ${to}`
}

export function formatRuc(ruc: string): string {
  return ruc.replace(/(\d{10})(\d{3})/, '$1-$2')
}

export function initials(name: string): string {
  return name
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('')
}
