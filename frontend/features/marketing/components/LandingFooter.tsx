import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useRouter } from 'expo-router'
import { Logo } from '@/components/branding/Logo'
import { Routes } from '@/constants/routes'
import { colors, overlay, radius, spacing, typography } from '@/constants/tokens'

export function LandingFooter() {
  const router = useRouter()
  const year = new Date().getFullYear()

  return (
    <View style={[styles.container, { borderTopColor: overlay.border.default }]}>
      <View style={styles.brand}>
        <Logo size={20} style={styles.mark} />
        <Text style={styles.text}>© {year} CodeLabs Ecuador · Facturación electrónica SRI</Text>
      </View>
      <Pressable onPress={() => router.push(Routes.auth.login)}>
        <Text style={styles.link}>Iniciar sesión</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    backgroundColor: colors.nav,
    borderTopWidth: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[2],
    justifyContent: 'space-between',
    paddingHorizontal: spacing[5],
    paddingVertical: spacing[6],
  },
  brand: { alignItems: 'center', flex: 1, flexDirection: 'row', gap: spacing[2], minWidth: 0 },
  mark: { borderRadius: radius.xs, overflow: 'hidden' },
  text: { color: overlay.text.faint, flexShrink: 1, fontSize: typography.size.xs },
  link: {
    color: overlay.text.muted,
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
})
