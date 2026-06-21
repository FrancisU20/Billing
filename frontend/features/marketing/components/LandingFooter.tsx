import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useRouter } from 'expo-router'
import { Logo } from '@/components/branding/Logo'
import { Routes } from '@/constants/routes'
import { colors, layout, overlay, radius, spacing, typography } from '@/constants/tokens'

export function LandingFooter() {
  const router = useRouter()
  const year = new Date().getFullYear()

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: colors.nav, borderTopColor: overlay.border.default },
      ]}
    >
      <View style={styles.content}>
        <View style={styles.brand}>
          <Logo size={20} style={styles.mark} />
          <Text style={styles.text}>© {year} CodeLabs Ecuador · Facturación electrónica SRI</Text>
        </View>
        <View style={styles.links}>
          <Pressable onPress={() => router.push(Routes.public.legalTerms)}>
            <Text style={styles.link}>Términos</Text>
          </Pressable>
          <Pressable onPress={() => router.push(Routes.public.legalPrivacy)}>
            <Text style={styles.link}>Privacidad</Text>
          </Pressable>
          <Pressable onPress={() => router.push(Routes.public.legalRefund)}>
            <Text style={styles.link}>Reembolsos</Text>
          </Pressable>
          <Pressable onPress={() => router.push(Routes.auth.login)}>
            <Text style={styles.link}>Iniciar sesión</Text>
          </Pressable>
        </View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { borderTopWidth: 1, paddingHorizontal: spacing[5], paddingVertical: spacing[6] },
  content: {
    alignItems: 'center',
    alignSelf: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
    justifyContent: 'space-between',
    maxWidth: layout.contentMaxWidth,
    width: '100%',
  },
  brand: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  links: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  mark: { borderRadius: radius.xs, overflow: 'hidden' },
  text: { color: overlay.text.faint, flexShrink: 1, fontSize: typography.size.xs },
  link: {
    color: overlay.text.muted,
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
})
