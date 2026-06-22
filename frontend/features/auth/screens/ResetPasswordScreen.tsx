import React, { useEffect } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing } from '@/constants/tokens'
import { Routes } from '@/constants/routes'
import { NavBar } from '@/components/layout/NavBar'
import { useToast } from '@/components/feedback/Toast'
import { ResetPasswordForm } from '../components/ResetPasswordForm'
import { useResetPassword } from '../hooks/useResetPassword'
import type { ResetPasswordFormValues } from '../schemas'

export function ResetPasswordScreen() {
  const router = useRouter()
  const toast = useToast()
  const { username } = useLocalSearchParams<{ username: string }>()
  const { resetPassword, loading, error } = useResetPassword()
  const { semantic } = useTheme()

  useEffect(() => {
    if (!username) {
      router.replace(Routes.auth.forgotPassword)
    }
  }, [username, router])

  const handleSubmit = async (values: ResetPasswordFormValues) => {
    try {
      await resetPassword({
        username,
        confirmationCode: values.confirmationCode,
        newPassword: values.newPassword,
      })
    } catch {
      return
    }
    toast.success('Contraseña actualizada. Inicia sesión con tu nueva contraseña.')
    router.replace(Routes.auth.login)
  }

  if (!username) return null

  return (
    <View style={[staticStyles.container, { backgroundColor: semantic.bg.primary }]}>
      <NavBar title="Recuperar contraseña" canGoBack />
      <View style={staticStyles.body}>
        <Text style={[staticStyles.title, { color: semantic.text.primary }]}>
          Establece tu nueva contraseña
        </Text>
        <ResetPasswordForm
          email={username}
          onSubmit={handleSubmit}
          isLoading={loading}
          apiError={error}
        />
      </View>
    </View>
  )
}

const staticStyles = StyleSheet.create({
  container: { flex: 1 },
  body: { flex: 1, padding: spacing[6], gap: spacing[5] },
  title: { fontSize: typography.size.xl, fontWeight: typography.weight.semibold },
})
