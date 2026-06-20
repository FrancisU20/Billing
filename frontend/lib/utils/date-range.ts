import { dateOnlyToLocalDate, ecuadorTodayISO, isDateOnly } from './ecuador-time'

export interface DateRangeValue {
  from: string
  to: string
}

export type DateRangeEdge = 'from' | 'to'

export interface CalendarDay {
  iso: string
  day: number
  inCurrentMonth: boolean
}

const DAY_MS = 24 * 60 * 60 * 1000
const WEEK_START_MONDAY = 1

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

export function dateToDateOnly(value: Date): string {
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
}

export function validDateOnly(value: string): boolean {
  if (!isDateOnly(value)) return false
  const parsed = dateOnlyToLocalDate(value)
  return dateToDateOnly(parsed) === value
}

export function compareDateOnly(a: string, b: string): number {
  if (a === b) return 0
  return a < b ? -1 : 1
}

export function addDays(value: string, days: number): string {
  const date = dateOnlyToLocalDate(value)
  date.setDate(date.getDate() + days)
  return dateToDateOnly(date)
}

export function shiftMonth(value: string, delta: number): string {
  const date = dateOnlyToLocalDate(value)
  date.setMonth(date.getMonth() + delta, 1)
  return dateToDateOnly(date)
}

export function monthStart(value: string): string {
  const date = dateOnlyToLocalDate(value)
  return dateToDateOnly(new Date(date.getFullYear(), date.getMonth(), 1))
}

export function monthEnd(value: string): string {
  const date = dateOnlyToLocalDate(value)
  return dateToDateOnly(new Date(date.getFullYear(), date.getMonth() + 1, 0))
}

export function weekRange(today: string = ecuadorTodayISO()): DateRangeValue {
  const date = dateOnlyToLocalDate(today)
  const day = date.getDay() || 7
  const offset = day - WEEK_START_MONDAY
  const from = dateToDateOnly(new Date(date.getTime() - offset * DAY_MS))
  return { from, to: addDays(from, 6) }
}

export function monthRange(today: string = ecuadorTodayISO()): DateRangeValue {
  return { from: monthStart(today), to: monthEnd(today) }
}

export function normalizeDateRange(value: DateRangeValue): DateRangeValue {
  const from = value.from.trim()
  const to = value.to.trim()
  if (!from || !to || compareDateOnly(from, to) <= 0) return { from, to }
  return { from: to, to: from }
}

export function selectDateInRange(
  value: DateRangeValue,
  date: string,
  activeEdge: DateRangeEdge,
): DateRangeValue {
  if (activeEdge === 'from') {
    return normalizeDateRange({ from: date, to: value.to })
  }
  return normalizeDateRange({ from: value.from, to: date })
}

export function isDateInRange(date: string, value: DateRangeValue): boolean {
  const { from, to } = normalizeDateRange(value)
  if (!from || !to) return false
  return compareDateOnly(from, date) <= 0 && compareDateOnly(date, to) <= 0
}

export function calendarDaysForMonth(monthIso: string): CalendarDay[] {
  const first = dateOnlyToLocalDate(monthStart(monthIso))
  const leading = (first.getDay() + 6) % 7
  const start = new Date(first.getFullYear(), first.getMonth(), 1 - leading)
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + index)
    return {
      iso: dateToDateOnly(date),
      day: date.getDate(),
      inCurrentMonth: date.getMonth() === first.getMonth(),
    }
  })
}

export function monthLabel(monthIso: string): string {
  return new Intl.DateTimeFormat('es-EC', {
    month: 'long',
    year: 'numeric',
  }).format(dateOnlyToLocalDate(monthIso))
}
