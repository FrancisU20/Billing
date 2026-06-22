// SRI Res. NAC-DGERCGC25-00000014/00000017: anulacion "en linea" solo hasta el dia 7 del
// mes siguiente a la emision. No se ajusta al siguiente dia habil si cae feriado/fin de
// semana (mismo criterio que el backend, ver use_cases/annul_document.py).
const ANNULMENT_DEADLINE_DAY = 7

export function isWithinAnnulmentWindow(issuedAt: string): boolean {
  const [year, month, day] = issuedAt.split('-').map(Number)
  if (!year || !month || !day) return false

  const deadline = new Date(year, month, ANNULMENT_DEADLINE_DAY) // month is 0-indexed -> next month
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  deadline.setHours(0, 0, 0, 0)

  return today <= deadline
}
