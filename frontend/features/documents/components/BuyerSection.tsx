import React, { useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import {
  Controller,
  useWatch,
  type Control,
  type FieldErrors,
  type UseFormSetValue,
} from 'react-hook-form'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { EmailField, PhoneField } from '@/components/ui/SpecializedFields'
import { spacing, typography } from '@/constants/tokens'
import type { Client, IdentificationType } from '@/features/clients/types'
import { useTheme } from '@/lib/theme-context'
import {
  BUYER_MODE_OPTIONS,
  CONSUMIDOR_FINAL_ID,
  CONSUMIDOR_FINAL_ID_TYPE,
  CONSUMIDOR_FINAL_NAME,
} from '../constants'
import type { EmitDocumentFormValues } from '../schemas'
import { ClientPickerModal } from './ClientPickerModal'

const CLIENT_IDENTIFICATION_TO_BUYER_ID_TYPE: Record<
  IdentificationType,
  EmitDocumentFormValues['buyer_id_type']
> = {
  ruc: '04',
  cedula: '05',
  pasaporte: '06',
  exterior: '08',
}

interface BuyerSectionProps {
  control: Control<EmitDocumentFormValues>
  setValue: UseFormSetValue<EmitDocumentFormValues>
  errors: FieldErrors<EmitDocumentFormValues>
}

export function BuyerSection({ control, setValue, errors }: BuyerSectionProps) {
  const { semantic } = useTheme()
  const [pickerOpen, setPickerOpen] = useState(false)
  const [hasInteracted, setHasInteracted] = useState(false)
  const [clientExtra, setClientExtra] = useState({ phone: '', address: '' })
  const buyerMode = useWatch({ control, name: 'buyer_mode' })
  const clientId = useWatch({ control, name: 'client_id' })

  function setBuyerMode(mode: EmitDocumentFormValues['buyer_mode']) {
    setValue('buyer_mode', mode, { shouldDirty: true, shouldValidate: true })
    setHasInteracted(false)
    setClientExtra({ phone: '', address: '' })
    if (mode === 'consumidor_final') {
      setValue('client_id', null, { shouldDirty: true, shouldValidate: true })
      setValue('buyer_id_type', CONSUMIDOR_FINAL_ID_TYPE, {
        shouldDirty: true,
        shouldValidate: true,
      })
      setValue('buyer_id', CONSUMIDOR_FINAL_ID, { shouldDirty: true, shouldValidate: true })
      setValue('buyer_name', CONSUMIDOR_FINAL_NAME, { shouldDirty: true, shouldValidate: true })
      setValue('buyer_email', '', { shouldDirty: true, shouldValidate: true })
    } else {
      setValue('client_id', null, { shouldDirty: true, shouldValidate: true })
      setValue('buyer_id', '', { shouldDirty: true, shouldValidate: true })
      setValue('buyer_name', '', { shouldDirty: true, shouldValidate: true })
      setValue('buyer_email', '', { shouldDirty: true, shouldValidate: true })
    }
  }

  function selectClient(client: Client) {
    setValue('client_id', client.id, { shouldDirty: true, shouldValidate: true })
    setValue('buyer_id_type', CLIENT_IDENTIFICATION_TO_BUYER_ID_TYPE[client.identification_type], {
      shouldDirty: true,
      shouldValidate: true,
    })
    setValue('buyer_id', client.identification, { shouldDirty: true, shouldValidate: true })
    setValue('buyer_name', client.trade_name || client.legal_name, {
      shouldDirty: true,
      shouldValidate: true,
    })
    setValue('buyer_email', client.emails[0] ?? '', { shouldDirty: true, shouldValidate: true })
    setClientExtra({ phone: client.phones[0] ?? '', address: client.addresses[0]?.line ?? '' })
    setPickerOpen(false)
  }

  return (
    <View style={styles.container}>
      <SegmentedControl options={BUYER_MODE_OPTIONS} value={buyerMode} onChange={setBuyerMode} />

      {buyerMode === 'cliente' ? (
        <View style={styles.clientPickerRow}>
          <Button
            variant="primary"
            size="md"
            onPress={() => {
              setHasInteracted(true)
              setPickerOpen(true)
            }}
          >
            {clientId ? 'Cambiar cliente' : 'Buscar cliente'}
          </Button>
          {hasInteracted && errors.client_id?.message ? (
            <Text style={[styles.statusText, { color: semantic.status.error }]}>
              {errors.client_id.message}
            </Text>
          ) : (
            <Text style={[styles.statusText, { color: semantic.text.tertiary }]}>
              Los datos se completan al elegir el cliente — no se editan aquí, para evitar facturar
              a alguien que no quede registrado.
            </Text>
          )}
        </View>
      ) : null}

      <View style={styles.fieldGrid}>
        <View style={styles.fieldHalf}>
          <Controller
            control={control}
            name="buyer_id"
            render={({ field: { value } }) => (
              <FormField
                label="Identificación"
                placeholder="9999999999999"
                leftIcon="finger-print-outline"
                isDisabled
                value={value}
                onChangeText={() => undefined}
                required
              />
            )}
          />
        </View>
        <View style={styles.fieldHalf}>
          <Controller
            control={control}
            name="buyer_name"
            render={({ field: { value } }) => (
              <FormField
                label="Nombre / razón social"
                placeholder="Consumidor Final"
                leftIcon="person-outline"
                isDisabled
                value={value}
                onChangeText={() => undefined}
                required
              />
            )}
          />
        </View>
      </View>

      <View style={styles.fieldGrid}>
        <View style={styles.fieldHalf}>
          <Controller
            control={control}
            name="buyer_email"
            render={({ field: { value } }) => (
              <EmailField
                label="Email"
                placeholder="Sin email registrado"
                isDisabled
                value={value}
                onChangeText={() => undefined}
              />
            )}
          />
        </View>
        {buyerMode === 'cliente' ? (
          <View style={styles.fieldHalf}>
            <PhoneField
              label="Teléfono"
              placeholder="Sin teléfono registrado"
              isDisabled
              value={clientExtra.phone}
              onChangeText={() => undefined}
            />
          </View>
        ) : null}
      </View>

      {buyerMode === 'cliente' ? (
        <FormField
          label="Dirección"
          placeholder="Sin dirección registrada"
          leftIcon="location-outline"
          isDisabled
          value={clientExtra.address}
          onChangeText={() => undefined}
        />
      ) : null}

      <ClientPickerModal
        visible={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={selectClient}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[3] },
  clientPickerRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
  },
  statusText: {
    flex: 1,
    fontSize: typography.size.xs,
    lineHeight: typography.size.xs * 1.5,
    minWidth: 200,
  },
  fieldGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  fieldHalf: { flex: 1, minWidth: 220 },
})
