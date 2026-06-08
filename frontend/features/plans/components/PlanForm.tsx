import React from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { StyleSheet, Switch, Text, View } from 'react-native'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { useTheme } from '@/lib/theme-context'
import { spacing, typography } from '@/constants/tokens'
import { createPlanSchema, type CreatePlanInput } from '../schemas'
import type { ApiError } from '@/lib/api/errors'

interface PlanFormProps {
  onSubmit: (values: CreatePlanInput) => void
  isLoading: boolean
  apiError: ApiError | null
}

const featureFields = [
  ['includes_credit_notes', 'Notas de crédito'],
  ['includes_withholdings', 'Retenciones'],
  ['includes_delivery_notes', 'Guías de remisión'],
  ['includes_api', 'Acceso API'],
] as const

export function PlanForm({ onSubmit, isLoading, apiError }: PlanFormProps) {
  const { semantic } = useTheme()
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<CreatePlanInput>({
    resolver: zodResolver(createPlanSchema),
    defaultValues: {
      slug: '',
      name: '',
      description: '',
      monthly_price: '0.00',
      annual_price: '0.00',
      document_limit: 0,
      limit_cycle: 'month',
      max_locations: 1,
      max_emission_points: 1,
      max_users: 1,
      includes_credit_notes: true,
      includes_withholdings: true,
      includes_delivery_notes: true,
      includes_api: false,
      order: 0,
    },
  })

  return (
    <View style={styles.container}>
      <Controller
        control={control}
        name="slug"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Slug"
            placeholder="basic"
            autoCapitalize="none"
            leftIcon="link-outline"
            error={errors.slug?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
            required
          />
        )}
      />

      <Controller
        control={control}
        name="name"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Nombre"
            placeholder="Basic"
            leftIcon="pricetag-outline"
            error={errors.name?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
            required
          />
        )}
      />

      <Controller
        control={control}
        name="description"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Descripción"
            placeholder="Descripción comercial"
            leftIcon="document-text-outline"
            error={errors.description?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
          />
        )}
      />

      <View style={styles.grid}>
        <Controller
          control={control}
          name="monthly_price"
          render={({ field: { onChange, onBlur, value } }) => (
            <FormField
              label="Precio mensual"
              keyboardType="decimal-pad"
              leftIcon="cash-outline"
              error={errors.monthly_price?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={String(value)}
              required
            />
          )}
        />
        <Controller
          control={control}
          name="annual_price"
          render={({ field: { onChange, onBlur, value } }) => (
            <FormField
              label="Precio anual"
              keyboardType="decimal-pad"
              leftIcon="calendar-outline"
              error={errors.annual_price?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={String(value)}
              required
            />
          )}
        />
      </View>

      <View style={styles.grid}>
        <NumberField
          control={control}
          name="document_limit"
          label="Documentos"
          error={errors.document_limit?.message}
        />
        <NumberField
          control={control}
          name="max_users"
          label="Usuarios"
          error={errors.max_users?.message}
        />
      </View>

      <View style={styles.grid}>
        <NumberField
          control={control}
          name="max_locations"
          label="Locales"
          error={errors.max_locations?.message}
        />
        <NumberField
          control={control}
          name="max_emission_points"
          label="Puntos emisión"
          error={errors.max_emission_points?.message}
        />
      </View>

      <NumberField control={control} name="order" label="Orden" error={errors.order?.message} />

      <View style={styles.switches}>
        {featureFields.map(([name, label]) => (
          <Controller
            key={name}
            control={control}
            name={name}
            render={({ field: { onChange, value } }) => (
              <View style={styles.switchRow}>
                <Text style={[styles.switchLabel, { color: semantic.text.primary }]}>{label}</Text>
                <Switch value={Boolean(value)} onValueChange={onChange} />
              </View>
            )}
          />
        ))}
      </View>

      {apiError ? <ApiErrorBanner error={apiError} /> : null}

      <Button
        variant="primary"
        size="lg"
        fullWidth
        isLoading={isLoading}
        onPress={handleSubmit(onSubmit)}
      >
        Crear plan
      </Button>
    </View>
  )
}

function NumberField({
  control,
  name,
  label,
  error,
}: {
  control: ReturnType<typeof useForm<CreatePlanInput>>['control']
  name: 'document_limit' | 'max_locations' | 'max_emission_points' | 'max_users' | 'order'
  label: string
  error?: string
}) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field: { onChange, onBlur, value } }) => (
        <FormField
          label={label}
          keyboardType="number-pad"
          leftIcon="speedometer-outline"
          error={error}
          onChangeText={onChange}
          onBlur={onBlur}
          value={String(value)}
          required
        />
      )}
    />
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[4] },
  grid: { gap: spacing[4] },
  switches: { gap: spacing[2] },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing[3],
  },
  switchLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
})
