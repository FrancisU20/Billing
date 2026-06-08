import React, { useEffect, useRef } from 'react'
import { SplashScreen, Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { GluestackUIProvider } from '@gluestack-ui/themed'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { ThemeProvider, useTheme } from '@/lib/theme-context'
import { ToastProvider } from '@/components/feedback/Toast'
import { gluestackTheme } from '@/lib/theme'
import { useAuthStore } from '@/features/auth/store'
import { configureApiClient } from '@/lib/api/client'
import { authApi } from '@/features/auth/api'

SplashScreen.preventAutoHideAsync()

function AppShell() {
  const { hydrate, hydrated, setTokens, clearAuth } = useAuthStore()
  const { isDark } = useTheme()
  const splashHidden = useRef(false)

  useEffect(() => {
    hydrate()
  }, [hydrate])

  useEffect(() => {
    if (!hydrated || splashHidden.current) return
    splashHidden.current = true
    SplashScreen.hideAsync()
  }, [hydrated])

  useEffect(() => {
    configureApiClient({
      getIdToken: () => useAuthStore.getState().idToken,
      onRefresh: async () => {
        const currentRefresh = useAuthStore.getState().refreshToken
        if (!currentRefresh) return false
        try {
          const tokens = await authApi.refresh(currentRefresh)
          await setTokens({
            idToken: tokens.idToken,
            accessToken: tokens.accessToken,
            refreshToken: currentRefresh,
          })
          return true
        } catch {
          return false
        }
      },
      onSessionExpired: () => clearAuth(),
    })
  }, [setTokens, clearAuth])

  if (!hydrated) return null

  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  )
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <GluestackUIProvider config={gluestackTheme}>
        <ThemeProvider>
          <ToastProvider>
            <AppShell />
          </ToastProvider>
        </ThemeProvider>
      </GluestackUIProvider>
    </SafeAreaProvider>
  )
}
