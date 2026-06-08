import React from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { createTenantSchema, type CreateTenantInput } from '../schemas'
import type { ApiError } from '@/lib/api/errors'
import type { Plan } from '@/features/plans/types'

interface TenantFormProps {
  plans: Plan[]
  onSubmit: (values: CreateTenantInput) => void
  isLoading: boolean
  apiError: ApiError | null
}

export function TenantForm({ plans, onSubmit, isLoading, apiError }: TenantFormProps) {
  const { semantic } = useTheme()
  const {
    control,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<CreateTenantInput>({
    resolver: zodResolver(createTenantSchema),
    defaultValues: {
      ruc: '',
      trade_name: '',
      legal_rep_name: '',
      email: '',
      phone: '',
      address: '',
      plan_id: '',
    },
  })
  const selectedPlanId = useWatch({ control, name: 'plan_id' })

  return (
    <View style={styles.container}>
      <Controller
        control={control}
        name="ruc"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="RUC"
            placeholder="1790012345001"
            keyboardType="number-pad"
            leftIcon="card-outline"
            error={errors.ruc?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
            required
          />
        )}
      />

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

      <View style={styles.planSection}>
        <Text style={[styles.label, { color: semantic.text.primary }]}>Plan *</Text>
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
                    {plan.document_limit === -1 ? 'Docs ilimitados' : `${plan.document_limit} docs`}
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
      </View>

      {apiError ? <ApiErrorBanner error={apiError} /> : null}

      <Button
        variant="primary"
        size="lg"
        fullWidth
        isLoading={isLoading}
        onPress={handleSubmit(onSubmit)}
      >
        Crear empresa
      </Button>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[4] },
  planSection: { gap: spacing[2] },
  label: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  planList: { gap: spacing[2] },
  planOption: {
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    padding: spacing[3],
  },
  planCopy: { flex: 1, minWidth: 0, gap: spacing[1] },
  planName: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  planDetail: { fontSize: typography.size.xs },
  errorText: { fontSize: typography.size.xs },
})
