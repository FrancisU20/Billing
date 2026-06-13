import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Button } from '@/components/ui/Button'
import { colors, overlay, spacing, typography } from '@/constants/tokens'

interface FinalCtaSectionProps {
  onCreateAccount: () => void
}

export function FinalCtaSection({ onCreateAccount }: FinalCtaSectionProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Empieza a facturar sin complicaciones</Text>
      <Text style={styles.subtitle}>
        Crea tu cuenta gratis y emite tus primeros comprobantes electrónicos en el ambiente de
        pruebas del SRI hoy mismo.
      </Text>
      <Button variant="primary" size="lg" onPress={onCreateAccount}>
        Crear mi cuenta gratis
      </Button>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    backgroundColor: colors.nav,
    gap: spacing[4],
    paddingHorizontal: spacing[5],
    paddingVertical: spacing[10],
  },
  title: {
    color: overlay.text.primary,
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    textAlign: 'center',
  },
  subtitle: {
    color: overlay.text.muted,
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.relaxed,
    maxWidth: 480,
    textAlign: 'center',
  },
})
