import React from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Pressable, StyleSheet, Switch, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { useTheme } from '@/lib/theme-context'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { PLAN_FEATURES, PLAN_LIMIT_CYCLE_OPTIONS, UNLIMITED_LIMIT } from '../constants'
import { planFormValuesSchema, type PlanFormValues } from '../schemas'
import type { ApiError } from '@/lib/api/errors'
import type { CreatePlanInput, LimitCycle, Plan, UpdatePlanInput } from '../types'

interface PlanFormProps {
  mode: 'create' | 'edit'
  plan?: Plan | null
  onSubmit: (values: CreatePlanInput | UpdatePlanInput) => void
  isLoading: boolean
  apiError: ApiError | null
}

export function PlanForm({ mode, plan, onSubmit, isLoading, apiError }: PlanFormProps) {
  const { semantic } = useTheme()
  const {
    control,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<PlanFormValues>({
    resolver: zodResolver(planFormValuesSchema),
    defaultValues: planToFormValues(plan),
  })
  const limitCycle = useWatch({ control, name: 'limit_cycle' })

  function submit(values: PlanFormValues) {
    const payload = formValuesToPlanPayload(values)
    if (mode === 'edit') {
      onSubmit({
        name: payload.name,
        description: payload.description,
        monthly_price: payload.monthly_price,
        annual_price: payload.annual_price,
        document_limit: payload.document_limit,
        limit_cycle: payload.limit_cycle,
        max_locations: payload.max_locations,
        max_emission_points: payload.max_emission_points,
        max_users: payload.max_users,
        includes_credit_notes: payload.includes_credit_notes,
        includes_withholdings: payload.includes_withholdings,
        includes_delivery_notes: payload.includes_delivery_notes,
        includes_api: payload.includes_api,
        order: payload.order,
      })
      return
    }
    onSubmit(payload)
  }

  return (
    <View style={styles.container}>
      <FormSection title="Identidad comercial" icon="pricetag-outline">
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
              isDisabled={mode === 'edit'}
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
      </FormSection>

      <FormSection title="Precio y ciclo" icon="cash-outline">
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
        <View style={styles.fieldBlock}>
          <Text style={[styles.label, { color: semantic.text.primary }]}>Ciclo de documentos</Text>
          <SegmentedControl<LimitCycle>
            options={PLAN_LIMIT_CYCLE_OPTIONS}
            value={limitCycle}
            onChange={(next) => setValue('limit_cycle', next, { shouldDirty: true })}
          />
        </View>
      </FormSection>

      <FormSection title="Límites" icon="speedometer-outline">
        <LimitField
          control={control}
          setValue={setValue}
          name="document_limit"
          unlimitedName="document_limit_unlimited"
          label="Documentos"
          error={errors.document_limit?.message}
        />
        <View style={styles.grid}>
          <LimitField
            control={control}
            setValue={setValue}
            name="max_users"
            unlimitedName="max_users_unlimited"
            label="Usuarios"
            error={errors.max_users?.message}
          />
          <LimitField
            control={control}
            setValue={setValue}
            name="max_locations"
            unlimitedName="max_locations_unlimited"
            label="Locales"
            error={errors.max_locations?.message}
          />
        </View>
        <LimitField
          control={control}
          setValue={setValue}
          name="max_emission_points"
          unlimitedName="max_emission_points_unlimited"
          label="Puntos de emisión"
          error={errors.max_emission_points?.message}
        />
      </FormSection>

      <FormSection title="Módulos incluidos" icon="apps-outline">
        <View style={styles.featureGrid}>
          {PLAN_FEATURES.map((feature) => (
            <Controller
              key={feature.key}
              control={control}
              name={feature.key}
              render={({ field: { onChange, value } }) => (
                <Pressable
                  onPress={() => onChange(!value)}
                  style={[
                    styles.featureTile,
                    {
                      backgroundColor: value ? semantic.accent.subtle : semantic.bg.primary,
                      borderColor: value ? semantic.accent.default : semantic.border.default,
                    },
                  ]}
                >
                  <Ionicons
                    name={feature.icon}
                    size={18}
                    color={value ? semantic.accent.default : semantic.text.secondary}
                  />
                  <Text
                    style={[
                      styles.featureLabel,
                      { color: value ? semantic.accent.default : semantic.text.secondary },
                    ]}
                  >
                    {feature.label}
                  </Text>
                </Pressable>
              )}
            />
          ))}
        </View>
      </FormSection>

      <FormSection title="Orden" icon="swap-vertical-outline">
        <NumberField control={control} name="order" label="Orden" error={errors.order?.message} />
      </FormSection>

      {apiError ? <ApiErrorBanner error={apiError} /> : null}

      <Button
        variant="primary"
        size="lg"
        fullWidth
        isLoading={isLoading}
        onPress={handleSubmit(submit)}
      >
        {mode === 'create' ? 'Crear plan' : 'Guardar cambios'}
      </Button>
    </View>
  )
}

function LimitField({
  control,
  setValue,
  name,
  unlimitedName,
  label,
  error,
}: {
  control: ReturnType<typeof useForm<PlanFormValues>>['control']
  setValue: ReturnType<typeof useForm<PlanFormValues>>['setValue']
  name: 'document_limit' | 'max_locations' | 'max_emission_points' | 'max_users'
  unlimitedName:
    | 'document_limit_unlimited'
    | 'max_locations_unlimited'
    | 'max_emission_points_unlimited'
    | 'max_users_unlimited'
  label: string
  error?: string
}) {
  const { semantic } = useTheme()
  const unlimited = useWatch({ control, name: unlimitedName })

  return (
    <View
      style={[
        styles.limitBox,
        { backgroundColor: semantic.bg.muted, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.limitHeader}>
        <Text style={[styles.limitTitle, { color: semantic.text.primary }]}>{label}</Text>
        <View style={styles.switchInline}>
          <Text style={[styles.switchText, { color: semantic.text.secondary }]}>Ilimitado</Text>
          <Switch
            value={unlimited}
            onValueChange={(next) => setValue(unlimitedName, next, { shouldDirty: true })}
            trackColor={{ false: semantic.border.strong, true: semantic.accent.muted }}
            thumbColor={unlimited ? semantic.accent.default : semantic.bg.elevated}
          />
        </View>
      </View>
      <NumberField
        control={control}
        name={name}
        label="Cantidad"
        error={error}
        disabled={unlimited}
      />
    </View>
  )
}

function NumberField({
  control,
  name,
  label,
  error,
  disabled = false,
}: {
  control: ReturnType<typeof useForm<PlanFormValues>>['control']
  name: 'document_limit' | 'max_locations' | 'max_emission_points' | 'max_users' | 'order'
  label: string
  error?: string
  disabled?: boolean
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
          onChangeText={(text) => onChange(Number(text))}
          onBlur={onBlur}
          value={String(value)}
          isDisabled={disabled}
          required
        />
      )}
    />
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

function planToFormValues(plan?: Plan | null): PlanFormValues {
  return {
    slug: plan?.slug ?? '',
    name: plan?.name ?? '',
    description: plan?.description ?? '',
    monthly_price: plan?.monthly_price ?? '0.00',
    annual_price: plan?.annual_price ?? '0.00',
    document_limit: normalizeLimitInput(plan?.document_limit, 0),
    document_limit_unlimited: plan?.document_limit === UNLIMITED_LIMIT,
    limit_cycle: plan?.limit_cycle ?? 'month',
    max_locations: normalizeLimitInput(plan?.max_locations, 1),
    max_locations_unlimited: plan?.max_locations === UNLIMITED_LIMIT,
    max_emission_points: normalizeLimitInput(plan?.max_emission_points, 1),
    max_emission_points_unlimited: plan?.max_emission_points === UNLIMITED_LIMIT,
    max_users: normalizeLimitInput(plan?.max_users, 1),
    max_users_unlimited: plan?.max_users === UNLIMITED_LIMIT,
    includes_credit_notes: plan?.includes_credit_notes ?? true,
    includes_withholdings: plan?.includes_withholdings ?? true,
    includes_delivery_notes: plan?.includes_delivery_notes ?? true,
    includes_api: plan?.includes_api ?? false,
    order: plan?.order ?? 0,
  }
}

function formValuesToPlanPayload(values: PlanFormValues): CreatePlanInput {
  return {
    slug: values.slug.trim(),
    name: values.name.trim(),
    description: values.description.trim(),
    monthly_price: values.monthly_price.trim(),
    annual_price: values.annual_price.trim(),
    document_limit: values.document_limit_unlimited ? UNLIMITED_LIMIT : values.document_limit,
    limit_cycle: values.limit_cycle,
    max_locations: values.max_locations_unlimited ? UNLIMITED_LIMIT : values.max_locations,
    max_emission_points: values.max_emission_points_unlimited
      ? UNLIMITED_LIMIT
      : values.max_emission_points,
    max_users: values.max_users_unlimited ? UNLIMITED_LIMIT : values.max_users,
    includes_credit_notes: values.includes_credit_notes,
    includes_withholdings: values.includes_withholdings,
    includes_delivery_notes: values.includes_delivery_notes,
    includes_api: values.includes_api,
    order: values.order,
  }
}

function normalizeLimitInput(value: number | undefined, fallback: number): number {
  if (value === undefined || value === UNLIMITED_LIMIT) return fallback
  return value
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
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  fieldBlock: { gap: spacing[2] },
  label: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  limitBox: { borderRadius: radius.md, borderWidth: 1, gap: spacing[3], padding: spacing[3] },
  limitHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing[3],
    justifyContent: 'space-between',
  },
  limitTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  switchInline: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  switchText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  featureGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  featureTile: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[2],
    minHeight: 42,
    minWidth: 170,
    paddingHorizontal: spacing[3],
  },
  featureLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
})
