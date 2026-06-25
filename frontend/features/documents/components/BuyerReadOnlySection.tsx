import React from 'react'
import { StyleSheet, View } from 'react-native'
import { FormField } from '@/components/ui/FormField'
import { EmailField } from '@/components/ui/SpecializedFields'
import { spacing } from '@/constants/tokens'

interface BuyerReadOnlySectionProps {
  buyerIdType: string
  buyerId: string
  buyerName: string
  buyerEmail: string | null
}

/**
 * Datos del comprador en modo solo-lectura para Nota de Credito — el comprador siempre
 * viene de la factura padre, nunca se vuelve a elegir ni a editar (a diferencia de
 * BuyerSection, que sigue sirviendo a la emision de factura sin cambios). Sin
 * react-hook-form: estos valores nunca se envian al backend, solo se muestran.
 */
export function BuyerReadOnlySection({
  buyerIdType,
  buyerId,
  buyerName,
  buyerEmail,
}: BuyerReadOnlySectionProps) {
  return (
    <View style={styles.container}>
      <View style={styles.fieldGrid}>
        <View style={styles.fieldHalf}>
          <FormField
            label="Identificación"
            leftIcon="finger-print-outline"
            isDisabled
            value={`${buyerIdType} · ${buyerId}`}
            onChangeText={() => undefined}
          />
        </View>
        <View style={styles.fieldHalf}>
          <FormField
            label="Nombre / razón social"
            leftIcon="person-outline"
            isDisabled
            value={buyerName}
            onChangeText={() => undefined}
          />
        </View>
      </View>
      <EmailField
        label="Email"
        placeholder="Sin email registrado"
        isDisabled
        value={buyerEmail ?? ''}
        onChangeText={() => undefined}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[3] },
  fieldGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  fieldHalf: { flex: 1, minWidth: 220 },
})
