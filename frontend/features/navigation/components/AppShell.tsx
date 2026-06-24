import React from 'react'
import { View } from 'react-native'
import { useIsDesktopLayout } from '@/lib/hooks/useIsDesktopLayout'
import type { AuthUser } from '@/features/auth/types'
import { SidebarNav } from './SidebarNav'

interface AppShellProps {
  user: AuthUser | null
  children: React.ReactNode
}

// Wraps screens that have passed all onboarding gates with the desktop sidebar.
// Screens reached before those gates pass (activate-subscription, confirm-plan,
// upload-certificate) render without this shell, since the user must not be able
// to navigate away from them — doing so would push a second instance of the
// current screen onto the stack instead of returning to the existing one.
export function AppShell({ user, children }: AppShellProps) {
  const isDesktop = useIsDesktopLayout()

  if (!isDesktop) return <>{children}</>

  return (
    <View style={{ flex: 1, flexDirection: 'row' }}>
      <SidebarNav user={user} />
      <View style={{ flex: 1, minWidth: 0 }}>{children}</View>
    </View>
  )
}
