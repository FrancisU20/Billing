import React, { useState } from 'react'
import { Pressable, StyleSheet } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { spacing, radius } from '@/constants/tokens'
import { NavBar, NavIconButton } from '@/components/layout/NavBar'
import { selectUser, useAuthStore } from '@/features/auth/store'
import type { AuthUser } from '@/features/auth/types'
import { AccountMenu } from './AccountMenu'
import { NavigationMenu } from './NavigationMenu'
import { UserAvatar } from './UserAvatar'

interface AppNavBarProps {
  title: string
  subtitle?: string
  canGoBack?: boolean
}

export function AppNavBar({ title, subtitle, canGoBack }: AppNavBarProps) {
  const user = useAuthStore(selectUser)
  const [navigationOpen, setNavigationOpen] = useState(false)
  const [accountOpen, setAccountOpen] = useState(false)

  const leftContent =
    user && !canGoBack ? (
      <NavIconButton
        icon="menu-outline"
        accessibilityLabel="Abrir menú"
        onPress={() => setNavigationOpen(true)}
      />
    ) : undefined

  const rightContent = user ? (
    <AccountButton onPress={() => setAccountOpen(true)} user={user} />
  ) : undefined

  return (
    <>
      <NavBar
        title={title}
        subtitle={subtitle}
        canGoBack={canGoBack}
        leftContent={leftContent}
        rightContent={rightContent}
      />

      {user ? (
        <>
          <NavigationMenu
            user={user}
            visible={navigationOpen}
            onClose={() => setNavigationOpen(false)}
          />
          <AccountMenu user={user} visible={accountOpen} onClose={() => setAccountOpen(false)} />
        </>
      ) : null}
    </>
  )
}

function AccountButton({ user, onPress }: { user: AuthUser; onPress: () => void }) {
  const { semantic } = useTheme()

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.accountBtn,
        {
          backgroundColor: pressed ? semantic.bg.muted : semantic.bg.elevated,
          borderColor: semantic.border.default,
        },
      ]}
      hitSlop={8}
    >
      <UserAvatar user={user} />
      <Ionicons name="chevron-down" size={14} color={semantic.text.tertiary} />
    </Pressable>
  )
}

const styles = StyleSheet.create({
  accountBtn: {
    height: 40,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    borderRadius: radius.full,
    borderWidth: 1,
    paddingLeft: spacing[1],
    paddingRight: spacing[2],
  },
})
