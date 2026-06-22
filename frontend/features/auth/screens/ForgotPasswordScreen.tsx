import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { Wordmark } from '@/components/branding/Logo'
import { overlay, typography, spacing } from '@/constants/tokens'
import { Routes } from '@/constants/routes'
import { ForgotPasswordForm } from '../components/ForgotPasswordForm'
import { useForgotPassword } from '../hooks/useForgotPassword'
import type { ForgotPasswordFormValues } from '../schemas'

export function ForgotPasswordScreen() {
  const router = useRouter()
  const { requestReset, loading, error } = useForgotPassword()
  const { semantic, isDark } = useTheme()

  const handleSubmit = async (values: ForgotPasswordFormValues) => {
    try {
      await requestReset(values.username)
    } catch {
      return
    }
    // Always proceed — never reveal whether the account exists.
    router.push({
      pathname: Routes.auth.resetPassword,
      params: { username: values.username },
    })
  }

  const pageBg = isDark ? semantic.bg.page : semantic.bg.page
  const titleColor = isDark ? overlay.text.primary : semantic.text.primary
  const subtitleColor = isDark ? overlay.text.subtle : semantic.text.secondary
  const dividerColor = isDark ? overlay.border.default : semantic.border.default
  const backLinkColor = isDark ? overlay.text.faint : semantic.text.tertiary

  return (
    <View style={[staticStyles.page, { backgroundColor: pageBg }]}>
      <View style={staticStyles.content}>
        <Wordmark height={22} />

        <View style={staticStyles.heading}>
          <Text style={[staticStyles.title, { color: titleColor }]}>¿Olvidaste tu contraseña?</Text>
          <Text style={[staticStyles.subtitle, { color: subtitleColor }]}>
            Ingresa tu email y te enviaremos un código para recuperarla
          </Text>
        </View>

        <View style={[staticStyles.divider, { backgroundColor: dividerColor }]} />

        <ForgotPasswordForm onSubmit={handleSubmit} isLoading={loading} apiError={error} />

        <Pressable
          onPress={() => router.push(Routes.auth.login)}
          style={({ pressed }) => [staticStyles.backLink, pressed && { opacity: 0.5 }]}
        >
          <Text style={[staticStyles.backLinkArrow, { color: semantic.accent.default }]}>← </Text>
          <Text style={[staticStyles.backLinkText, { color: backLinkColor }]}>
            Volver a iniciar sesión
          </Text>
        </Pressable>
      </View>
    </View>
  )
}

const staticStyles = StyleSheet.create({
  page: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing[6] },
  content: { width: '100%', maxWidth: 420, gap: spacing[7] },
  heading: { gap: spacing[2] },
  title: {
    fontSize: typography.size['4xl'],
    fontWeight: typography.weight.bold,
    letterSpacing: 0,
    lineHeight: typography.size['4xl'] * 1.1,
  },
  subtitle: { fontSize: typography.size.base, lineHeight: typography.size.base * 1.6 },
  divider: { height: 1 },
  backLink: { flexDirection: 'row', alignSelf: 'flex-start' },
  backLinkText: { fontSize: typography.size.sm },
  backLinkArrow: { fontSize: typography.size.sm },
})
