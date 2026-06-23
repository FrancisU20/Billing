import React, { useEffect } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Pressable, StyleSheet, Switch, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { FormActions } from '@/components/ui/FormActions'
import { FormField } from '@/components/ui/FormField'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { EmailField, IdentificationField, PhoneField } from '@/components/ui/SpecializedFields'
import { useTheme } from '@/lib/theme-context'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { clientFormValuesSchema, type ClientFormValues } from '../schemas'
import {
  CLIENT_FORM_STATUS_OPTIONS,
  CLIENT_IDENTIFICATION_OPTIONS,
  CLIENT_PERSON_LABELS,
  CLIENT_PERSON_OPTIONS,
} from '../constants'
import { clientToFormValues, derivePersonType } from '../form'
import type { ApiError } from '@/lib/api/errors'
import type { Client, ClientStatus, PersonType } from '../types'

/** Cedula y RUC determinan el tipo de persona por su propia estructura (ver
 * `derivePersonType`) — solo pasaporte/exterior dejan la eleccion manual al usuario. */
const PERSON_TYPE_IS_DERIVED: Record<ClientFormValues['identification_type'], boolean> = {
  ruc: true,
  cedula: true,
  pasaporte: false,
  exterior: false,
}

interface ClientFormProps {
  mode: 'create' | 'edit'
  client?: Client | null
  onSubmit: (values: ClientFormValues) => void
  isLoading: boolean
  apiError: ApiError | null
}

export function ClientForm({ mode, client, onSubmit, isLoading, apiError }: ClientFormProps) {
  const { semantic } = useTheme()
  const {
    control,
    handleSubmit,
    setValue,
    trigger,
    formState: { errors, isValid },
  } = useForm<ClientFormValues>({
    resolver: zodResolver(clientFormValuesSchema),
    defaultValues: clientToFormValues(client),
    mode: 'onChange',
    reValidateMode: 'onChange',
  })
  const identificationType = useWatch({ control, name: 'identification_type' })
  const identification = useWatch({ control, name: 'identification' })
  const personType = useWatch({ control, name: 'person_type' })
  const specialTaxpayer = useWatch({ control, name: 'special_taxpayer' })
  const status = useWatch({ control, name: 'status' })
  const personTypeIsDerived = PERSON_TYPE_IS_DERIVED[identificationType]

  useEffect(() => {
    if (!personTypeIsDerived) return
    const derived = derivePersonType(identificationType, identification, personType)
    if (derived !== personType) {
      setValue('person_type', derived, { shouldDirty: true, shouldValidate: true })
    }
  }, [identificationType, identification, personType, personTypeIsDerived, setValue])

  return (
    <View style={styles.container}>
      <FormSection title="Identificación fiscal" icon="card-outline">
        <View style={styles.optionGrid}>
          {CLIENT_IDENTIFICATION_OPTIONS.map((option) => (
            <OptionTile
              key={option.value}
              icon={option.icon}
              label={option.label}
              selected={identificationType === option.value}
              onPress={() => {
                setValue('identification_type', option.value, { shouldDirty: true })
                // El error de formato (RUC/cedula invalido) vive en el campo
                // "identification", no en "identification_type" — hay que revalidar
                // ambos juntos o el mensaje de error queda pegado al tipo anterior.
                void trigger(['identification_type', 'identification'])
              }}
            />
          ))}
        </View>

        <Controller
          control={control}
          name="identification"
          render={({ field: { onChange, onBlur, value } }) => (
            <IdentificationField
              identificationType={identificationType}
              label="Identificación"
              placeholder={identificationType === 'ruc' ? '1792146739001' : '1710034065'}
              error={errors.identification?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
              required
            />
          )}
        />

        <View style={styles.fieldBlock}>
          <Text style={[styles.label, { color: semantic.text.primary }]}>Tipo de persona *</Text>
          {personTypeIsDerived ? (
            <View
              style={[
                styles.derivedPersonType,
                { backgroundColor: semantic.bg.muted, borderColor: semantic.border.default },
              ]}
            >
              <Ionicons name="checkmark-circle-outline" size={16} color={semantic.text.secondary} />
              <Text style={[styles.derivedPersonTypeText, { color: semantic.text.primary }]}>
                {CLIENT_PERSON_LABELS[personType]}
              </Text>
              <Text style={[styles.derivedPersonTypeHint, { color: semantic.text.secondary }]}>
                — detectado por {identificationType === 'cedula' ? 'la cédula' : 'el RUC'}
              </Text>
            </View>
          ) : (
            <SegmentedControl<PersonType>
              options={CLIENT_PERSON_OPTIONS}
              value={personType}
              onChange={(nextPersonType) =>
                setValue('person_type', nextPersonType, {
                  shouldDirty: true,
                  shouldValidate: true,
                })
              }
            />
          )}
        </View>
      </FormSection>

      <FormSection title="Datos comerciales" icon="briefcase-outline">
        <Controller
          control={control}
          name="legal_name"
          render={({ field: { onChange, onBlur, value } }) => (
            <FormField
              label="Razón social / nombres"
              placeholder="Cliente S.A."
              leftIcon="business-outline"
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
          name="trade_name"
          render={({ field: { onChange, onBlur, value } }) => (
            <FormField
              label="Nombre comercial"
              placeholder="Nombre visible"
              leftIcon="storefront-outline"
              error={errors.trade_name?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
            />
          )}
        />
        <View
          style={[
            styles.switchRow,
            { backgroundColor: semantic.bg.muted, borderColor: semantic.border.default },
          ]}
        >
          <View style={styles.switchCopy}>
            <Text style={[styles.switchTitle, { color: semantic.text.primary }]}>
              Contribuyente especial
            </Text>
            <Text style={[styles.switchHint, { color: semantic.text.secondary }]}>
              Se usará como dato fiscal del cliente.
            </Text>
          </View>
          <Switch
            value={specialTaxpayer}
            onValueChange={(next) =>
              setValue('special_taxpayer', next, { shouldDirty: true, shouldValidate: true })
            }
            trackColor={{ false: semantic.border.strong, true: semantic.accent.muted }}
            thumbColor={specialTaxpayer ? semantic.accent.default : semantic.bg.elevated}
          />
        </View>
      </FormSection>

      <FormSection title="Contacto y dirección" icon="mail-outline">
        <Controller
          control={control}
          name="email"
          render={({ field: { onChange, onBlur, value } }) => (
            <EmailField
              label="Email principal"
              placeholder="facturacion@cliente.com"
              error={errors.email?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
            />
          )}
        />
        <Controller
          control={control}
          name="phone"
          render={({ field: { onChange, onBlur, value } }) => (
            <PhoneField
              label="Teléfono principal"
              placeholder="0999999999"
              error={errors.phone?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
            />
          )}
        />
        <View style={styles.addressGrid}>
          <Controller
            control={control}
            name="address_label"
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Etiqueta"
                placeholder="Principal"
                leftIcon="bookmark-outline"
                error={errors.address_label?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
              />
            )}
          />
          <Controller
            control={control}
            name="address_city"
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Ciudad"
                placeholder="Quito"
                leftIcon="map-outline"
                error={errors.address_city?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
              />
            )}
          />
        </View>
        <Controller
          control={control}
          name="address_line"
          render={({ field: { onChange, onBlur, value } }) => (
            <FormField
              label="Dirección"
              placeholder="Dirección fiscal"
              leftIcon="location-outline"
              error={errors.address_line?.message}
              onChangeText={onChange}
              onBlur={onBlur}
              value={value}
            />
          )}
        />
      </FormSection>

      {mode === 'edit' ? (
        <FormSection title="Estado" icon="toggle-outline">
          <SegmentedControl<ClientStatus>
            options={CLIENT_FORM_STATUS_OPTIONS}
            value={status}
            onChange={(nextStatus) =>
              setValue('status', nextStatus, { shouldDirty: true, shouldValidate: true })
            }
          />
        </FormSection>
      ) : null}

      {apiError ? <ApiErrorBanner error={apiError} /> : null}

      <FormActions
        submitLabel={mode === 'create' ? 'Crear cliente' : 'Guardar cambios'}
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

function OptionTile({
  icon,
  label,
  selected,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap
  label: string
  selected: boolean
  onPress: () => void
}) {
  const { semantic } = useTheme()
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.optionTile,
        {
          backgroundColor: selected
            ? semantic.accent.subtle
            : pressed
              ? semantic.bg.secondary
              : semantic.bg.primary,
          borderColor: selected ? semantic.accent.default : semantic.border.default,
        },
      ]}
    >
      <Ionicons
        name={icon}
        size={18}
        color={selected ? semantic.accent.default : semantic.text.secondary}
      />
      <Text
        style={[
          styles.optionLabel,
          { color: selected ? semantic.accent.default : semantic.text.secondary },
        ]}
        numberOfLines={1}
      >
        {label}
      </Text>
    </Pressable>
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
  optionGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  optionTile: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[2],
    minHeight: 42,
    minWidth: 132,
    paddingHorizontal: spacing[3],
  },
  optionLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  fieldBlock: { gap: spacing[2] },
  label: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  derivedPersonType: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[1],
    minHeight: 34,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
  },
  derivedPersonTypeText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  derivedPersonTypeHint: { fontSize: typography.size.xs },
  switchRow: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    justifyContent: 'space-between',
    padding: spacing[3],
  },
  switchCopy: { flex: 1, gap: spacing[1] },
  switchTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  switchHint: { fontSize: typography.size.xs },
  addressGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
})
