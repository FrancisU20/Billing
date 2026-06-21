import React from 'react'
import { Text, View } from 'react-native'
import { useRouter } from 'expo-router'
import { BlockingLoadingOverlay } from '@/components/ui/BlockingLoadingOverlay'
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

  function navigateToCompany() {
    onClose()
    router.push(Routes.tenant.company)
  }

  function handleLogout() {
    onClose()
    logout()
  }

  return (
    <>
      <MenuSurface visible={visible} onClose={onClose} side="right">
        <View style={menuLayoutStyles.accountHeader}>
          <UserAvatar user={user} size="lg" />
          <View style={menuLayoutStyles.accountCopy}>
            <Text
              style={[menuLayoutStyles.accountEmail, { color: semantic.text.primary }]}
              numberOfLines={1}
            >
              {user.email}
            </Text>
            <Text
              style={[menuLayoutStyles.accountRole, { color: semantic.text.secondary }]}
              numberOfLines={1}
            >
              {getUserRoleLabel(user)}
            </Text>
          </View>
        </View>

        <MenuDivider />

        {user.isSuperadmin ? null : (
          <MenuItem icon="business-outline" label="Mi empresa" onPress={navigateToCompany} />
        )}
        <MenuItem
          icon="log-out-outline"
          label={loading ? 'Cerrando sesión...' : 'Cerrar sesión'}
          danger
          disabled={loading}
          onPress={handleLogout}
        />
      </MenuSurface>
      <BlockingLoadingOverlay
        visible={loading}
        label="Cerrando sesión..."
        detail="Estamos cerrando tu sesión de forma segura."
      />
    </>
  )
}
