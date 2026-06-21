import { Redirect, Stack } from 'expo-router'
import { View } from 'react-native'
import { useAuthStore, selectIsAuthenticated, selectUser } from '@/features/auth/store'
import { Routes } from '@/constants/routes'
import { SidebarNav } from '@/features/navigation/components/SidebarNav'
import { useIsDesktopLayout } from '@/lib/hooks/useIsDesktopLayout'

export default function AppLayout() {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const user = useAuthStore(selectUser)
  const isDesktop = useIsDesktopLayout()

  if (!isAuthenticated) {
    return <Redirect href={Routes.auth.login} />
  }

  if (!isDesktop) {
    return <Stack screenOptions={{ headerShown: false }} />
  }

  return (
    <View style={{ flex: 1, flexDirection: 'row' }}>
      <SidebarNav user={user} />
      <View style={{ flex: 1, minWidth: 0 }}>
        <Stack screenOptions={{ headerShown: false }} />
      </View>
    </View>
  )
}
