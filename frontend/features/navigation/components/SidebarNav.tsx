import React from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import { usePathname, useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { Wordmark } from '@/components/branding/Logo'
import { spacing } from '@/constants/tokens'
import type { AuthUser } from '@/features/auth/types'
import { getAppNavigationItems, type AppNavigationItem } from '../items'
import { MenuItem } from './MenuSurface'

const SIDEBAR_WIDTH = 240

interface SidebarNavProps {
  user: AuthUser | null
}

export function SidebarNav({ user }: SidebarNavProps) {
  const { semantic } = useTheme()
  const router = useRouter()
  const pathname = usePathname()

  if (!user) return null

  const items = getAppNavigationItems(user)

  function navigateTo(item: AppNavigationItem) {
    router.push(item.href)
  }

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.primary, borderRightColor: semantic.border.default },
      ]}
    >
      <View style={styles.brand}>
        <Wordmark height={24} />
      </View>

      <ScrollView contentContainerStyle={styles.items} showsVerticalScrollIndicator={false}>
        {items.map((item) => (
          <MenuItem
            key={item.label}
            icon={item.icon}
            label={item.label}
            active={pathname.includes(item.activeWhen)}
            onPress={() => navigateTo(item)}
          />
        ))}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { width: SIDEBAR_WIDTH, borderRightWidth: 1, paddingVertical: spacing[5] },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    paddingHorizontal: spacing[5],
    marginBottom: spacing[6],
  },
  items: { gap: spacing[1], paddingHorizontal: spacing[3] },
})
