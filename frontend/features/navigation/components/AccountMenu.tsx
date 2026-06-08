import React from 'react'
import { Text, View } from 'react-native'
import { useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import type { AuthUser } from '@/features/auth/types'
import { useLogout } from '@/features/auth/hooks/useLogout'
import { getUserRoleLabel } from '@/features/auth/utils/userDisplay'
import { MenuDivider, MenuItem, MenuSurface, menuLayoutStyles } from './MenuSurface'
import { UserAvatar } from './UserAvatar'

interface AccountMenuProps {
  user: AuthUser
  visible: boolean
  onClose: () => void
}

export function AccountMenu({ user, visible, onClose }: AccountMenuProps) {
  const router = useRouter()
  const { semantic } = useTheme()
  const { logout, loading } = useLogout()

  function navigateToProfile() {
    onClose()
    router.push(Routes.app.profile)
  }

  function handleLogout() {
    onClose()
    logout()
  }

  return (
    <MenuSurface visible={visible} onClose={onClose} side="right">
      <View style={menuLayoutStyles.accountHeader}>
        <UserAvatar user={user} size="lg" />
        <View style={menuLayoutStyles.accountCopy}>
          <Text style={[menuLayoutStyles.accountEmail, { color: semantic.text.primary }]} numberOfLines={1}>{user.email}</Text>
          <Text style={[menuLayoutStyles.accountRole, { color: semantic.text.secondary }]} numberOfLines={1}>
            {getUserRoleLabel(user)}
          </Text>
        </View>
      </View>

      <MenuDivider />

      <MenuItem icon="person-outline" label="Mi perfil" onPress={navigateToProfile} />
      <MenuItem icon="log-out-outline" label="Cerrar sesión" danger disabled={loading} onPress={handleLogout} />
    </MenuSurface>
  )
}
