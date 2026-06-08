import type { ClientStatus, IdentificationType } from './schemas'

export type {
  Client,
  ClientAddress,
  ClientsPage,
  ClientStatus,
  ClientFormValues,
  CreateClientInput,
  IdentificationType,
  PersonType,
  UpdateClientInput,
} from './schemas'

export interface ClientListFilters {
  q?: string
  identification?: string
  status?: ClientStatus
  identification_type?: IdentificationType
  created_from?: string
  created_to?: string
}
