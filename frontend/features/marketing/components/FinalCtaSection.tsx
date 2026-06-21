import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Button } from '@/components/ui/Button'
import { colors, layout, overlay, spacing, typography } from '@/constants/tokens'

interface FinalCtaSectionProps {
  onCreateAccount: () => void
}

export function FinalCtaSection({ onCreateAccount }: FinalCtaSectionProps) {
  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Empieza a facturar sin complicaciones</Text>
        <Text style={styles.subtitle}>
          Crea tu cuenta gratis y emite tus primeros comprobantes electrónicos en el ambiente de
          pruebas del SRI hoy mismo.
        </Text>
        <Button variant="primary" size="lg" onPress={onCreateAccount}>
          Crear mi cuenta gratis
        </Button>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.nav,
    paddingHorizontal: spacing[5],
    paddingVertical: spacing[10],
  },
  content: {
    alignItems: 'center',
    alignSelf: 'center',
    gap: spacing[4],
    maxWidth: layout.contentMaxWidth,
    width: '100%',
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
