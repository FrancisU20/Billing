import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useRouter } from 'expo-router'
import { Routes } from '@/constants/routes'
import { colors, overlay, spacing, typography } from '@/constants/tokens'

export function LandingFooter() {
  const router = useRouter()
  const year = new Date().getFullYear()

  return (
    <View style={[styles.container, { borderTopColor: overlay.border.default }]}>
      <Text style={styles.text}>© {year} CodeLabs Ecuador · Facturación electrónica SRI</Text>
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
  text: { color: overlay.text.faint, fontSize: typography.size.xs },
  link: {
    color: overlay.text.muted,
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
})
