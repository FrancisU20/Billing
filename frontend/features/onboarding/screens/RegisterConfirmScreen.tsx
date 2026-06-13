import React, { useEffect } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { Button } from '@/components/ui/Button'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'
import { useOnboardingStore } from '../store'

export function RegisterConfirmScreen() {
  const { semantic } = useTheme()
  const router = useRouter()
  const result = useOnboardingStore((state) => state.result)
  const reset = useOnboardingStore((state) => state.reset)

  useEffect(() => {
    if (!result) {
      router.replace(Routes.public.register as Href)
    }
  }, [result, router])

  if (!result) return null

  const isTenant = 'tenant_id' in result

  const handleContinue = () => {
    reset()
    router.replace((isTenant ? Routes.auth.login : Routes.public.pricing) as Href)
  }

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <View style={[styles.iconWrap, { backgroundColor: semantic.accent.subtle }]}>
        <Ionicons
          name={isTenant ? 'checkmark-circle-outline' : 'mail-outline'}
          size={40}
          color={semantic.accent.default}
        />
      </View>

      {isTenant ? (
        <>
          <Text style={[styles.title, { color: semantic.text.primary }]}>
            ¡Cuenta creada con éxito!
          </Text>
          <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
            Enviamos una clave temporal a {result.email}. Úsala para iniciar sesión y completar la
            configuración de tu empresa.
          </Text>
        </>
      ) : (
        <>
          <Text style={[styles.title, { color: semantic.text.primary }]}>
            ¡Gracias por tu interés!
          </Text>
          <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
            {result.message}
          </Text>
        </>
      )}

      <Button variant="primary" size="lg" onPress={handleContinue}>
        {isTenant ? 'Ir a iniciar sesión' : 'Volver a planes'}
      </Button>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    flex: 1,
    gap: spacing[4],
    justifyContent: 'center',
    padding: spacing[6],
  },
  iconWrap: {
    alignItems: 'center',
    borderRadius: radius.full,
    height: 72,
    justifyContent: 'center',
    width: 72,
  },
  title: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.normal,
    textAlign: 'center',
  },
})
