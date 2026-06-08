import React from 'react'
import { View } from 'react-native'
import { usePathname, useRouter } from 'expo-router'
import type { AuthUser } from '@/features/auth/types'
import { getAppNavigationItems, type AppNavigationItem } from '../items'
import { MenuEyebrow, MenuItem, MenuSurface, menuLayoutStyles } from './MenuSurface'

interface NavigationMenuProps {
  user: AuthUser
  visible: boolean
  onClose: () => void
}

export function NavigationMenu({ user, visible, onClose }: NavigationMenuProps) {
  const pathname = usePathname()
  const router = useRouter()
  const items = getAppNavigationItems(user)

  function navigateTo(item: AppNavigationItem) {
    onClose()
    router.push(item.href)
  }

  return (
    <MenuSurface visible={visible} onClose={onClose} side="left">
      <MenuEyebrow label="Navegación" />
      <View style={menuLayoutStyles.menuItems}>
        {items.map((item) => (
          <MenuItem
            key={item.label}
            icon={item.icon}
            label={item.label}
            active={pathname.includes(item.activeWhen)}
            onPress={() => navigateTo(item)}
          />
        ))}
      </View>
    </MenuSurface>
  )
}
