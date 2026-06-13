import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'

const steps = [
  {
    title: 'Elige tu plan',
    description:
      'Compara límites de documentos, usuarios y locales, y elige el que se ajuste a tu negocio.',
  },
  {
    title: 'Crea tu cuenta',
    description: 'Regístrate con el RUC y los datos de tu empresa. Sin papeleo, sin esperas.',
  },
  {
    title: 'Empieza a facturar',
    description:
      'Inicia sesión con la clave temporal que te enviamos y emite tus primeros documentos en pruebas.',
  },
] as const

export function HowItWorksSection() {
  const { semantic } = useTheme()

  return (
    <View style={styles.container}>
      <Text style={[styles.title, { color: semantic.text.primary }]}>Cómo funciona</Text>

      <View style={styles.steps}>
        {steps.map((step, index) => (
          <View key={step.title} style={styles.step}>
            <View style={[styles.stepNumber, { backgroundColor: semantic.accent.subtle }]}>
              <Text style={[styles.stepNumberText, { color: semantic.accent.default }]}>
                {index + 1}
              </Text>
            </View>
            <View style={styles.stepCopy}>
              <Text style={[styles.stepTitle, { color: semantic.text.primary }]}>{step.title}</Text>
              <Text style={[styles.stepDescription, { color: semantic.text.secondary }]}>
                {step.description}
              </Text>
            </View>
          </View>
        ))}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[5], paddingHorizontal: spacing[5], paddingVertical: spacing[6] },
  title: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['2xl'] * typography.lineHeight.tight,
  },
  steps: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[5] },
  step: { flexBasis: 220, flexGrow: 1, flexDirection: 'row', gap: spacing[3] },
  stepNumber: {
    alignItems: 'center',
    borderRadius: radius.full,
    height: 32,
    justifyContent: 'center',
    width: 32,
  },
  stepNumberText: { fontSize: typography.size.base, fontWeight: typography.weight.bold },
  stepCopy: { flex: 1, gap: spacing[1] },
  stepTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  stepDescription: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
})
