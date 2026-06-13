import type { CreateTenantInput, Tenant, TenantFormValues, UpdateTenantInput } from './schemas'
import { createTenantSchema, updateTenantSchema } from './schemas'

export type { TenantFormValues } from './schemas'

export function tenantToFormValues(tenant?: Tenant | null): TenantFormValues {
  return {
    ruc: tenant?.ruc ?? '',
    trade_name: tenant?.trade_name ?? '',
    legal_name: tenant?.legal_name ?? '',
    legal_rep_name: tenant?.legal_rep_name ?? '',
    email: tenant?.email ?? '',
    phone: tenant?.phone ?? '',
    address: tenant?.address ?? '',
    accounting_required: tenant?.accounting_required ?? false,
    sri_environment: tenant?.sri_environment ?? 'testing',
    plan_id: tenant?.plan_id ?? '',
  }
}

export function formValuesToCreateTenantInput(values: TenantFormValues): CreateTenantInput {
  return createTenantSchema.parse({
    ruc: values.ruc.trim(),
    trade_name: values.trade_name.trim(),
    legal_name: values.legal_name.trim(),
    legal_rep_name: values.legal_rep_name.trim(),
    email: values.email.trim(),
    phone: values.phone.trim(),
    address: values.address.trim(),
    accounting_required: values.accounting_required,
    plan_id: values.plan_id,
  })
}

export function formValuesToUpdateTenantInput(values: TenantFormValues): UpdateTenantInput {
  return updateTenantSchema.parse({
    trade_name: values.trade_name.trim(),
    legal_name: values.legal_name.trim(),
    legal_rep_name: values.legal_rep_name.trim(),
    email: values.email.trim(),
    phone: values.phone.trim(),
    address: values.address.trim(),
    accounting_required: values.accounting_required,
    sri_environment: values.sri_environment,
  })
}
