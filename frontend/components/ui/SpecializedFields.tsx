import React from 'react'
import { FormField } from '@/components/ui/FormField'
import type { FormFieldProps } from '@/components/ui/FormField'

type SpecializedFieldProps = Omit<FormFieldProps, 'keyboardType' | 'autoCapitalize' | 'leftIcon'>

export function EmailField(props: SpecializedFieldProps) {
  return (
    <FormField
      {...props}
      keyboardType="email-address"
      autoCapitalize="none"
      leftIcon="mail-outline"
    />
  )
}

export function RucField(props: SpecializedFieldProps) {
  return (
    <FormField
      {...props}
      keyboardType="number-pad"
      autoCapitalize="none"
      leftIcon="card-outline"
      maxLength={13}
    />
  )
}

interface IdentificationFieldProps extends SpecializedFieldProps {
  identificationType: 'ruc' | 'cedula' | 'pasaporte' | 'exterior'
}

export function IdentificationField({ identificationType, ...props }: IdentificationFieldProps) {
  const isNumeric = identificationType === 'ruc' || identificationType === 'cedula'
  return (
    <FormField
      {...props}
      keyboardType={isNumeric ? 'number-pad' : 'default'}
      autoCapitalize="characters"
      leftIcon="finger-print-outline"
      maxLength={identificationType === 'ruc' ? 13 : identificationType === 'cedula' ? 10 : 25}
    />
  )
}

export function MoneyField(props: SpecializedFieldProps) {
  return (
    <FormField
      {...props}
      keyboardType="decimal-pad"
      autoCapitalize="none"
      leftIcon="cash-outline"
    />
  )
}

export function PercentField(props: SpecializedFieldProps) {
  return (
    <FormField
      {...props}
      keyboardType="decimal-pad"
      autoCapitalize="none"
      leftIcon="pricetag-outline"
    />
  )
}

export function PhoneField(props: SpecializedFieldProps) {
  return <FormField {...props} keyboardType="phone-pad" leftIcon="call-outline" />
}
