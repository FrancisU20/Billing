import {
  createClientSchema,
  updateClientSchema,
  type Client,
  type ClientFormValues,
  type CreateClientInput,
  type IdentificationType,
  type PersonType,
  type UpdateClientInput,
} from './schemas'

/**
 * Espejo de `backend/lambdas/clients/domain/entity.py::_derive_person_type`. La cedula y
 * el RUC ya codifican el tipo de persona (regla del propio SRI para el digito
 * verificador, ver `lib/utils/ruc.ts`): cedula siempre natural; RUC con 3er digito 0-5
 * persona natural, 6 o 9 juridica (las entidades publicas no son personas naturales).
 * Pasaporte/exterior no tienen esa estructura, ahi se respeta la eleccion manual.
 */
export function derivePersonType(
  identificationType: IdentificationType,
  identification: string,
  requested: PersonType,
): PersonType {
  if (identificationType === 'cedula') return 'natural'
  if (identificationType === 'ruc') {
    const thirdDigit = identification.trim()[2]
    if (thirdDigit === undefined || !/^\d$/.test(thirdDigit)) return requested
    return Number(thirdDigit) < 6 ? 'natural' : 'juridica'
  }
  return requested
}

export function clientToFormValues(client?: Client | null): ClientFormValues {
  const address = client?.addresses[0]
  return {
    identification: client?.identification ?? '',
    identification_type: client?.identification_type ?? 'ruc',
    person_type: client?.person_type ?? 'juridica',
    legal_name: client?.legal_name ?? '',
    trade_name: client?.trade_name ?? '',
    special_taxpayer: client?.special_taxpayer ?? false,
    email: client?.emails[0] ?? '',
    phone: client?.phones[0] ?? '',
    address_label: address?.label ?? 'Principal',
    address_line: address?.line ?? '',
    address_city: address?.city ?? '',
    status: client?.status ?? 'active',
  }
}

export function formValuesToCreateClientInput(values: ClientFormValues): CreateClientInput {
  return createClientSchema.parse(toPayload(values))
}

export function formValuesToUpdateClientInput(values: ClientFormValues): UpdateClientInput {
  return updateClientSchema.parse(toPayload(values))
}

function toPayload(values: ClientFormValues): CreateClientInput {
  const email = values.email.trim()
  const phone = values.phone.trim()
  const addressLine = values.address_line.trim()

  return {
    identification: values.identification.trim(),
    identification_type: values.identification_type,
    person_type: values.person_type,
    legal_name: values.legal_name.trim(),
    trade_name: values.trade_name.trim(),
    special_taxpayer: values.special_taxpayer,
    emails: email ? [email] : [],
    phones: phone ? [phone] : [],
    addresses: addressLine
      ? [
          {
            label: values.address_label.trim() || 'Principal',
            line: addressLine,
            city: values.address_city.trim(),
          },
        ]
      : [],
  }
}
