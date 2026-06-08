import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { overlay, typography, spacing, radius } from '@/constants/tokens'
import { Routes } from '@/constants/routes'
import { LoginForm } from '../components/LoginForm'
import { useLogin } from '../hooks/useLogin'
import type { LoginFormValues } from '../schemas'

export function LoginScreen() {
  const router = useRouter()
  const { login, loading, error } = useLogin()
  const { semantic, isDark } = useTheme()

  const handleSubmit = async (values: LoginFormValues) => {
    try {
      const result = await login({ username: values.username, password: values.password })
      if (result.type === 'challenge') {
        router.push({
          pathname: Routes.auth.challenge,
          params: {
            session: result.challenge.session,
            challenge_name: result.challenge.challenge_name,
          },
        })
        return
      }
      router.replace(Routes.root)
    } catch {
      // error shown via ApiErrorBanner
    }
  }

  const pageBg = isDark ? semantic.bg.page : semantic.bg.page
  const titleColor = isDark ? overlay.text.primary : semantic.text.primary
  const subtitleColor = isDark ? overlay.text.subtle : semantic.text.secondary
  const brandColor = isDark ? overlay.text.subtle : semantic.text.tertiary
  const dividerColor = isDark ? overlay.border.default : semantic.border.default
  const pricingColor = isDark ? overlay.text.faint : semantic.text.tertiary

  return (
    <View style={[staticStyles.page, { backgroundColor: pageBg }]}>
      <View style={staticStyles.content}>
        <View style={staticStyles.brand}>
          <View style={staticStyles.mark}>
            <View style={[staticStyles.markDot, { backgroundColor: semantic.accent.default }]} />
            <View style={[staticStyles.markDot, { backgroundColor: semantic.accent.default }]} />
          </View>
          <Text style={[staticStyles.brandName, { color: brandColor }]}>
            CODELABS <Text style={{ color: semantic.accent.default }}>BILLING</Text>
          </Text>
        </View>

        <View style={staticStyles.heading}>
          <Text style={[staticStyles.title, { color: titleColor }]}>Inicia sesión</Text>
          <Text style={[staticStyles.subtitle, { color: subtitleColor }]}>
            Accede a tu panel de facturación electrónica
          </Text>
        </View>

        <View style={[staticStyles.divider, { backgroundColor: dividerColor }]} />

        <LoginForm onSubmit={handleSubmit} isLoading={loading} apiError={error} dark={isDark} />

        <Pressable
          onPress={() => router.push(Routes.public.pricing)}
          style={({ pressed }) => [staticStyles.pricingLink, pressed && { opacity: 0.5 }]}
        >
          <Text style={[staticStyles.pricingText, { color: pricingColor }]}>
            Ver planes de precios
          </Text>
          <Text style={[staticStyles.pricingArrow, { color: semantic.accent.default }]}> →</Text>
        </Pressable>
      </View>
    </View>
  )
}

const staticStyles = StyleSheet.create({
  page: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing[6] },
  content: { width: '100%', maxWidth: 420, gap: spacing[7] },
  brand: { gap: spacing[3] },
  mark: { flexDirection: 'row', gap: spacing[1] },
  markDot: { width: 8, height: 8, borderRadius: radius.full },
  brandName: { fontSize: typography.size.xs, fontWeight: typography.weight.bold, letterSpacing: 2 },
  heading: { gap: spacing[2] },
  title: {
    fontSize: typography.size['4xl'],
    fontWeight: typography.weight.bold,
    letterSpacing: -1,
    lineHeight: typography.size['4xl'] * 1.1,
  },
  subtitle: { fontSize: typography.size.base, lineHeight: typography.size.base * 1.6 },
  divider: { height: 1 },
  pricingLink: { flexDirection: 'row', alignSelf: 'flex-start' },
  pricingText: { fontSize: typography.size.sm },
  pricingArrow: { fontSize: typography.size.sm },
})
