export const ECUADOR_TIME_ZONE = 'America/Guayaquil'

const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/

interface EcuadorParts {
  year: string
  month: string
  day: string
  hour: string
  minute: string
}

export function isDateOnly(value: string): boolean {
  return DATE_ONLY_RE.test(value)
}

export function ecuadorParts(now: Date = new Date()): EcuadorParts {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: ECUADOR_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(now)
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? ''

  return {
    year: value('year'),
    month: value('month'),
    day: value('day'),
    hour: value('hour'),
    minute: value('minute'),
  }
}

export function ecuadorTodayISO(now?: Date): string {
  const parts = ecuadorParts(now)
  return `${parts.year}-${parts.month}-${parts.day}`
}

export function ecuadorDateTimeDisplay(now?: Date): string {
  const parts = ecuadorParts(now)
  return `${parts.day}/${parts.month}/${parts.year} ${parts.hour}:${parts.minute}`
}

export function dateOnlyToLocalDate(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}
