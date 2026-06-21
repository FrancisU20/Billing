import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { layout, radius, spacing, typography } from '@/constants/tokens'

const features = [
  {
    icon: 'document-text-outline',
    title: 'Comprobantes electrónicos SRI',
    description:
      'Facturas, notas de crédito, retenciones y guías de remisión firmadas y autorizadas.',
  },
  {
    icon: 'flask-outline',
    title: 'Ambiente de pruebas incluido',
    description: 'Emite documentos de prueba sin riesgo antes de pasar a producción.',
  },
  {
    icon: 'business-outline',
    title: 'Multi-local y multiusuario',
    description: 'Administra varios locales y equipos desde una sola cuenta de empresa.',
  },
  {
    icon: 'code-slash-outline',
    title: 'API para integraciones',
    description: 'Conecta tu sistema de ventas o ERP con nuestra API según tu plan.',
  },
  {
    icon: 'people-outline',
    title: 'Gestión de clientes',
    description:
      'Lleva el catálogo de tus clientes con sus datos tributarios listos para facturar.',
  },
  {
    icon: 'rocket-outline',
    title: 'Onboarding self-service',
    description: 'Crea tu cuenta y empieza a operar sin esperar aprobaciones manuales.',
  },
] as const

export function FeaturesSection() {
  const { semantic } = useTheme()

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <View style={styles.heading}>
          <Text style={[styles.title, { color: semantic.text.primary }]}>
            Todo lo que necesitas para facturar
          </Text>
          <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
            Una plataforma pensada para cumplir con el SRI sin distraerte de tu negocio.
          </Text>
        </View>

        <View style={styles.grid}>
          {features.map((feature) => (
            <View
              key={feature.title}
              style={[
                styles.card,
                { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
              ]}
            >
              <View style={[styles.iconWrap, { backgroundColor: semantic.accent.subtle }]}>
                <Ionicons name={feature.icon} size={20} color={semantic.accent.default} />
              </View>
              <Text style={[styles.cardTitle, { color: semantic.text.primary }]}>
                {feature.title}
              </Text>
              <Text style={[styles.cardDescription, { color: semantic.text.secondary }]}>
                {feature.description}
              </Text>
            </View>
          ))}
        </View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { paddingHorizontal: spacing[5], paddingVertical: spacing[8] },
  content: {
    alignSelf: 'center',
    gap: spacing[5],
    maxWidth: layout.contentMaxWidth,
    width: '100%',
  },
  heading: { gap: spacing[2] },
  title: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['2xl'] * typography.lineHeight.tight,
  },
  subtitle: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.normal,
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  card: {
    borderRadius: radius.md,
    borderWidth: 1,
    flexBasis: 260,
    flexGrow: 1,
    gap: spacing[2],
    padding: spacing[5],
  },
  iconWrap: {
    alignItems: 'center',
    borderRadius: radius.lg,
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  cardTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  cardDescription: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
})
