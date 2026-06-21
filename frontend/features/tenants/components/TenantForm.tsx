import React from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { FormActions } from '@/components/ui/FormActions'
import { FormField } from '@/components/ui/FormField'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { EmailField, PhoneField, RucField } from '@/components/ui/SpecializedFields'
import { useTheme } from '@/lib/theme-context'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { ACCOUNTING_REQUIRED_OPTIONS, TENANT_ENVIRONMENT_OPTIONS } from '../constants'
import { tenantToFormValues, type TenantFormValues } from '../form'
import { tenantFormValuesSchema } from '../schemas'
import type { ApiError } from '@/lib/api/errors'
import type { Plan } from '@/features/plans/types'
import type { SriEnvironment, Tenant } from '../types'

interface TenantFormProps {
  mode: 'create' | 'edit'
  tenant?: Tenant | null
  plans?: Plan[]
  onSubmit: (values: TenantFormValues) => void
  isLoading: boolean
  apiError: ApiError | null
}

export function TenantForm({
  mode,
  tenant,
  plans = [],
  onSubmit,
  isLoading,
  apiError,
}: TenantFormProps) {
  const { semantic } = useTheme()
  const {
    control,
    handleSubmit,
    setValue,
    formState: { errors, isValid },
  } = useForm<TenantFormValues>({
    resolver: zodResolver(tenantFormValuesSchema),
    defaultValues: tenantToFormValues(tenant),
    mode: 'onChange',
    reValidateMode: 'onChange',
  })
  const selectedPlanId = useWatch({ control, name: 'plan_id' })
  const sriEnvironment = useWatch({ control, name: 'sri_environment' })
  const accountingRequired = useWatch({ control, name: 'accounting_required' })

  return (
    <View style={styles.container}>
      <FormSection title="Identificación" icon="business-outline">
        <Controller
          control={control}
          name="ruc"
          render={({ field: { onChange, onBlur, value } }) => (
            <RucField
              label="RUC"
              placeholder="1792146739001"
              error={errors.ruc?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
              isDisabled={mode === 'edit'}
              required
            />
          )}
        />
      </FormSection>

      <FormSection title="Datos de empresa" icon="briefcase-outline">
        <Controller
          control={control}
          name="trade_name"
          render={({ field: { onChange, onBlur, value } }) => (
            <FormField
              label="Nombre comercial"
              placeholder="Wali"
              leftIcon="business-outline"
              error={errors.trade_name?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
              required
            />
          )}
        />

        <Controller
          control={control}
          name="legal_name"
          render={({ field: { onChange, onBlur, value } }) => (
            <FormField
              label="Razón social"
              placeholder="Wali S.A."
              leftIcon="document-text-outline"
              error={errors.legal_name?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
              required
            />
          )}
        />

        <Controller
          control={control}
          name="legal_rep_name"
          render={({ field: { onChange, onBlur, value } }) => (
            <FormField
              label="Representante legal"
              placeholder="Nombre completo"
              leftIcon="person-outline"
              error={errors.legal_rep_name?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
              required
            />
          )}
        />

        <View style={styles.fieldBlock}>
          <Text style={[styles.label, { color: semantic.text.primary }]}>
            Obligado a llevar contabilidad *
          </Text>
          <SegmentedControl<'yes' | 'no'>
            options={ACCOUNTING_REQUIRED_OPTIONS}
            value={accountingRequired ? 'yes' : 'no'}
            onChange={(next) =>
              setValue('accounting_required', next === 'yes', {
                shouldDirty: true,
                shouldValidate: true,
              })
            }
          />
        </View>

        <View style={styles.fieldBlock}>
          <Text style={[styles.label, { color: semantic.text.primary }]}>Entorno SRI *</Text>
          <SegmentedControl<SriEnvironment | 'all'>
            options={TENANT_ENVIRONMENT_OPTIONS.filter((option) => option.value !== 'all')}
            value={sriEnvironment}
            onChange={(next) => {
              if (next !== 'all') {
                setValue('sri_environment', next, { shouldDirty: true, shouldValidate: true })
              }
            }}
          />
        </View>
      </FormSection>

      <FormSection title="Contacto" icon="mail-outline">
        <Controller
          control={control}
          name="email"
          render={({ field: { onChange, onBlur, value } }) => (
            <EmailField
              label="Email"
              placeholder="admin@empresa.com"
              error={errors.email?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
              required
            />
          )}
        />
        <Controller
          control={control}
          name="phone"
          render={({ field: { onChange, onBlur, value } }) => (
            <PhoneField
              label="Teléfono"
              placeholder="0999999999"
              error={errors.phone?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
              required
            />
          )}
        />
        <Controller
          control={control}
          name="address"
          render={({ field: { onChange, onBlur, value } }) => (
            <FormField
              label="Dirección"
              placeholder="Dirección fiscal"
              leftIcon="location-outline"
              error={errors.address?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
              required
            />
          )}
        />
      </FormSection>

      {mode === 'create' ? (
        <FormSection title="Plan" icon="pricetag-outline">
          <View style={styles.planList}>
            {plans.map((plan) => {
              const selected = selectedPlanId === plan.id
              return (
                <Pressable
                  key={plan.id}
                  onPress={() => setValue('plan_id', plan.id, { shouldValidate: true })}
                  style={[
                    styles.planOption,
                    {
                      backgroundColor: selected ? semantic.accent.subtle : semantic.bg.elevated,
                      borderColor: selected ? semantic.accent.default : semantic.border.default,
                    },
                  ]}
                >
                  <View style={styles.planCopy}>
                    <Text style={[styles.planName, { color: semantic.text.primary }]}>
                      {plan.name}
                    </Text>
                    <Text style={[styles.planDetail, { color: semantic.text.secondary }]}>
                      {plan.document_limit === -1
                        ? 'Docs ilimitados'
                        : `${plan.document_limit} docs`}
                    </Text>
                  </View>
                  {selected ? (
                    <Ionicons name="checkmark-circle" size={20} color={semantic.accent.default} />
                  ) : null}
                </Pressable>
              )
            })}
          </View>
          {errors.plan_id?.message ? (
            <Text style={[styles.errorText, { color: semantic.status.error }]}>
              {errors.plan_id.message}
            </Text>
          ) : null}
        </FormSection>
      ) : null}

      {apiError ? <ApiErrorBanner error={apiError} /> : null}

      <FormActions
        submitLabel={mode === 'create' ? 'Crear empresa' : 'Guardar cambios'}
        isSubmitting={isLoading}
        isSubmitDisabled={!isValid}
        onSubmit={handleSubmit(onSubmit)}
      />
    </View>
  )
}

function FormSection({
  title,
  icon,
  children,
}: {
  title: string
  icon: keyof typeof Ionicons.glyphMap
  children: React.ReactNode
}) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.section,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.sectionHeader}>
        <View style={[styles.sectionIcon, { backgroundColor: semantic.accent.subtle }]}>
          <Ionicons name={icon} size={17} color={semantic.accent.default} />
        </View>
        <Text style={[styles.sectionTitle, { color: semantic.text.primary }]}>{title}</Text>
      </View>
      <View style={styles.sectionBody}>{children}</View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[4] },
  section: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    padding: spacing[4],
  },
  sectionHeader: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  sectionIcon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: sizes.icon,
    justifyContent: 'center',
    width: sizes.icon,
  },
  sectionTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  sectionBody: { gap: spacing[4] },
  fieldBlock: { gap: spacing[2] },
  label: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  planList: { gap: spacing[2] },
  planOption: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    padding: spacing[3],
  },
  planCopy: { flex: 1, minWidth: 0, gap: spacing[1] },
  planName: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  planDetail: { fontSize: typography.size.xs },
  errorText: { fontSize: typography.size.xs },
})
