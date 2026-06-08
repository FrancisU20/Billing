import React from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { z } from 'zod'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { TENANT_ENVIRONMENT_OPTIONS } from '../constants'
import { tenantToFormValues, type TenantFormValues } from '../form'
import type { ApiError } from '@/lib/api/errors'
import type { Plan } from '@/features/plans/types'
import type { SriEnvironment, Tenant } from '../types'

const tenantFormSchema = z.object({
  ruc: z.string().trim().min(10, 'RUC inválido').max(13, 'RUC inválido'),
  trade_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(200, 'Máximo 200 caracteres'),
  legal_rep_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(200, 'Máximo 200 caracteres'),
  email: z.string().trim().email('Email inválido').max(200, 'Máximo 200 caracteres'),
  phone: z.string().trim().min(7, 'Mínimo 7 caracteres').max(20, 'Máximo 20 caracteres'),
  address: z.string().trim().min(5, 'Mínimo 5 caracteres').max(500, 'Máximo 500 caracteres'),
  sri_environment: z.enum(['testing', 'production']),
  plan_id: z.string().min(1, 'El plan es requerido'),
})

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
    formState: { errors },
  } = useForm<TenantFormValues>({
    resolver: zodResolver(tenantFormSchema),
    defaultValues: tenantToFormValues(tenant),
  })
  const selectedPlanId = useWatch({ control, name: 'plan_id' })
  const sriEnvironment = useWatch({ control, name: 'sri_environment' })

  return (
    <View style={styles.container}>
      <FormSection title="Identificación" icon="business-outline">
        <Controller
          control={control}
          name="ruc"
          render={({ field: { onChange, onBlur, value } }) => (
            <FormField
              label="RUC"
              placeholder="1792146739001"
              keyboardType="number-pad"
              leftIcon="card-outline"
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
              placeholder="CodeLabs"
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
            <FormField
              label="Email"
              placeholder="admin@empresa.com"
              keyboardType="email-address"
              autoCapitalize="none"
              leftIcon="mail-outline"
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
            <FormField
              label="Teléfono"
              placeholder="0999999999"
              keyboardType="phone-pad"
              leftIcon="call-outline"
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

      <Button
        variant="primary"
        size="lg"
        fullWidth
        isLoading={isLoading}
        onPress={handleSubmit(onSubmit)}
      >
        {mode === 'create' ? 'Crear empresa' : 'Guardar cambios'}
      </Button>
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
    height: 34,
    justifyContent: 'center',
    width: 34,
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
