import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing } from '@/constants/tokens'
import { Routes } from '@/constants/routes'
import { NavBar } from '@/components/layout/NavBar'
import { ChallengeForm } from '../components/ChallengeForm'
import { useChallenge } from '../hooks/useChallenge'
import type { NewPasswordFormValues } from '../schemas'

export function ChallengeScreen() {
  const router = useRouter()
  const { session, challenge_name } = useLocalSearchParams<{ session: string; challenge_name: string }>()
  const { respond, loading, error } = useChallenge()
  const { semantic } = useTheme()

  const handleSubmit = async (values: NewPasswordFormValues) => {
    const result = await respond({
      session,
      challenge_name,
      responses: { NEW_PASSWORD: values.newPassword },
    })
    if (result.type === 'success') router.replace(Routes.root)
  }

  return (
    <View style={[staticStyles.container, { backgroundColor: semantic.bg.primary }]}>
      <NavBar title="Nueva contraseña" canGoBack />
      <View style={staticStyles.body}>
        <Text style={[staticStyles.title, { color: semantic.text.primary }]}>
          Configura tu contraseña
        </Text>
        <ChallengeForm onSubmit={handleSubmit} isLoading={loading} apiError={error} />
      </View>
    </View>
  )
}

const staticStyles = StyleSheet.create({
  container: { flex: 1 },
  body: { flex: 1, padding: spacing[6], gap: spacing[5] },
  title: { fontSize: typography.size.xl, fontWeight: typography.weight.semibold },
})
