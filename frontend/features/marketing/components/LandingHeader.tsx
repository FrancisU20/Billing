import React from 'react'
import { StyleSheet, View } from 'react-native'
import { useRouter } from 'expo-router'
import { Wordmark } from '@/components/branding/Logo'
import { Routes } from '@/constants/routes'
import { colors, layout, overlay, spacing } from '@/constants/tokens'
import { OnDarkButton } from './OnDarkButton'

export function LandingHeader() {
  const router = useRouter()

  return (
    <View style={[styles.container, { backgroundColor: colors.nav }]}>
      <View style={styles.row}>
        <Wordmark height={22} ink={overlay.text.primary} />

        <OnDarkButton size="sm" onPress={() => router.push(Routes.auth.login)}>
          Iniciar sesión
        </OnDarkButton>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { paddingHorizontal: spacing[5], paddingTop: spacing[6], paddingBottom: spacing[4] },
  row: {
    alignItems: 'center',
    alignSelf: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    maxWidth: layout.contentMaxWidth,
    width: '100%',
  },
})
