import type { Ionicons } from '@expo/vector-icons'
import type { ClientStatus, IdentificationType, PersonType } from './types'

export const CLIENTS_PAGE_SIZE = 30

export const CLIENT_IDENTIFICATION_OPTIONS: Array<{
  value: IdentificationType
  label: string
  icon: keyof typeof Ionicons.glyphMap
}> = [
  { value: 'ruc', label: 'RUC', icon: 'business-outline' },
  { value: 'cedula', label: 'Cédula', icon: 'person-outline' },
  { value: 'pasaporte', label: 'Pasaporte', icon: 'airplane-outline' },
  { value: 'exterior', label: 'Exterior', icon: 'earth-outline' },
]

export const CLIENT_PERSON_OPTIONS: Array<{ value: PersonType; label: string }> = [
  { value: 'natural', label: 'Natural' },
  { value: 'juridica', label: 'Jurídica' },
]

export const CLIENT_STATUS_OPTIONS: Array<{ value: ClientStatus | 'all'; label: string }> = [
  { value: 'all', label: 'Todos' },
  { value: 'active', label: 'Activos' },
  { value: 'inactive', label: 'Inactivos' },
]

export const CLIENT_SEARCH_MODE_OPTIONS = [
  { value: 'q', label: 'General' },
  { value: 'identification', label: 'Identificación exacta' },
] as const

export const CLIENT_STATUS_LABELS: Record<ClientStatus, string> = {
  active: 'Activo',
  inactive: 'Inactivo',
}

export const CLIENT_IDENTIFICATION_LABELS: Record<IdentificationType, string> = {
  ruc: 'RUC',
  cedula: 'Cédula',
  pasaporte: 'Pasaporte',
  exterior: 'Exterior',
}

export const CLIENT_PERSON_LABELS: Record<PersonType, string> = {
  natural: 'Persona natural',
  juridica: 'Persona jurídica',
}

export type ClientSearchMode = (typeof CLIENT_SEARCH_MODE_OPTIONS)[number]['value']
