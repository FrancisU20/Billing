import React, { useState } from 'react'
import { StyleSheet, View } from 'react-native'
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
import { spacing } from '@/constants/tokens'
import type { Client, IdentificationType } from '@/features/clients/types'
import {
  BUYER_MODE_OPTIONS,
  CONSUMIDOR_FINAL_ID,
  CONSUMIDOR_FINAL_ID_TYPE,
  CONSUMIDOR_FINAL_NAME,
} from '../constants'
import type { EmitDocumentFormValues } from '../schemas'
import { BuyerIdTypePicker } from './BuyerIdTypePicker'
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
  const [pickerOpen, setPickerOpen] = useState(false)
  const buyerMode = useWatch({ control, name: 'buyer_mode' })
  const clientId = useWatch({ control, name: 'client_id' })

  function setBuyerMode(mode: EmitDocumentFormValues['buyer_mode']) {
    setValue('buyer_mode', mode, { shouldDirty: true })
    if (mode === 'consumidor_final') {
      setValue('client_id', null, { shouldDirty: true })
      setValue('buyer_id_type', CONSUMIDOR_FINAL_ID_TYPE, { shouldDirty: true })
      setValue('buyer_id', CONSUMIDOR_FINAL_ID, { shouldDirty: true, shouldValidate: true })
      setValue('buyer_name', CONSUMIDOR_FINAL_NAME, { shouldDirty: true, shouldValidate: true })
      setValue('buyer_email', '', { shouldDirty: true })
    } else if (mode === 'manual') {
      setValue('client_id', null, { shouldDirty: true })
    }
  }

  function selectClient(client: Client) {
    setValue('client_id', client.id, { shouldDirty: true })
    setValue('buyer_id_type', CLIENT_IDENTIFICATION_TO_BUYER_ID_TYPE[client.identification_type], {
      shouldDirty: true,
    })
    setValue('buyer_id', client.identification, { shouldDirty: true, shouldValidate: true })
    setValue('buyer_name', client.trade_name || client.legal_name, {
      shouldDirty: true,
      shouldValidate: true,
    })
    setValue('buyer_email', client.emails[0] ?? '', { shouldDirty: true })
    setPickerOpen(false)
  }

  const fieldsDisabled = buyerMode === 'consumidor_final'

  return (
    <View style={styles.container}>
      <SegmentedControl options={BUYER_MODE_OPTIONS} value={buyerMode} onChange={setBuyerMode} />

      {buyerMode === 'cliente' ? (
        <Button variant="outline" size="md" onPress={() => setPickerOpen(true)}>
          {clientId ? 'Cambiar cliente' : 'Buscar cliente'}
        </Button>
      ) : null}

      {buyerMode === 'manual' ? (
        <Controller
          control={control}
          name="buyer_id_type"
          render={({ field: { value } }) => (
            <BuyerIdTypePicker
              value={value}
              onChange={(next) => setValue('buyer_id_type', next, { shouldDirty: true })}
            />
          )}
        />
      ) : null}

      <Controller
        control={control}
        name="buyer_id"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Identificación del comprador"
            placeholder="9999999999999"
            leftIcon="finger-print-outline"
            isDisabled={fieldsDisabled}
            error={errors.buyer_id?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
            required
          />
        )}
      />
      <Controller
        control={control}
        name="buyer_name"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Nombre / razón social"
            placeholder="Consumidor Final"
            leftIcon="person-outline"
            isDisabled={fieldsDisabled}
            error={errors.buyer_name?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
            required
          />
        )}
      />
      <Controller
        control={control}
        name="buyer_email"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Email (opcional)"
            placeholder="comprador@email.com"
            keyboardType="email-address"
            autoCapitalize="none"
            leftIcon="mail-outline"
            isDisabled={fieldsDisabled}
            error={errors.buyer_email?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
          />
        )}
      />

      <ClientPickerModal
        visible={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={selectClient}
      />
    </View>
  )
}

const styles = StyleSheet.create({ container: { gap: spacing[3] } })
