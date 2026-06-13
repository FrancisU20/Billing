import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { Logo } from '@/components/branding/Logo'
import { Routes } from '@/constants/routes'
import { colors, overlay, radius, spacing, typography } from '@/constants/tokens'
import { OnDarkButton } from './OnDarkButton'

export function LandingHeader() {
  const router = useRouter()
  const { semantic } = useTheme()

  return (
    <View style={styles.container}>
      <View style={styles.brand}>
        <Logo size={32} style={styles.mark} />
        <Text style={styles.brandName}>
          CODELABS <Text style={{ color: semantic.accent.default }}>BILLING</Text>
        </Text>
      </View>

      <OnDarkButton size="sm" onPress={() => router.push(Routes.auth.login)}>
        Iniciar sesión
      </OnDarkButton>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    backgroundColor: colors.nav,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing[5],
    paddingTop: spacing[6],
    paddingBottom: spacing[4],
  },
  brand: { alignItems: 'center', flexDirection: 'row', gap: spacing[3] },
  mark: { borderRadius: radius.sm, overflow: 'hidden' },
  brandName: {
    color: overlay.text.primary,
    fontSize: typography.size.sm,
    fontWeight: typography.weight.bold,
    letterSpacing: 2,
  },
})
