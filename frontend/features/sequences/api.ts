import { api } from '@/lib/api/client'
import {
  addEmissionPointSchema,
  createEstablishmentSchema,
  editEmissionPointSchema,
  establishmentSchema,
  establishmentsListSchema,
} from './schemas'
import type {
  AddEmissionPointInput,
  CreateEstablishmentInput,
  EditEmissionPointInput,
} from './types'

function establishmentsBasePath(tenantId: string): string {
  return `/tenants/${encodeURIComponent(tenantId)}/establishments`
}

export const sequencesApi = {
  list: (tenantId: string) => api.get(establishmentsBasePath(tenantId), establishmentsListSchema),

  create: (tenantId: string, body: CreateEstablishmentInput, idempotencyKey: string) =>
    api.post(
      establishmentsBasePath(tenantId),
      createEstablishmentSchema.parse(body),
      establishmentSchema,
      { idempotencyKey },
    ),

  addEmissionPoint: (
    tenantId: string,
    establishmentCode: string,
    body: AddEmissionPointInput,
    idempotencyKey: string,
  ) =>
    api.post(
      `${establishmentsBasePath(tenantId)}/${encodeURIComponent(establishmentCode)}/emission-points`,
      addEmissionPointSchema.parse(body),
      establishmentSchema,
      { idempotencyKey },
    ),

  editEmissionPoint: (
    tenantId: string,
    establishmentCode: string,
    pointCode: string,
    body: EditEmissionPointInput,
    idempotencyKey: string,
  ) =>
    api.patch(
      `${establishmentsBasePath(tenantId)}/${encodeURIComponent(establishmentCode)}/emission-points/${encodeURIComponent(pointCode)}`,
      editEmissionPointSchema.parse(body),
      establishmentSchema,
      { idempotencyKey },
    ),
}
