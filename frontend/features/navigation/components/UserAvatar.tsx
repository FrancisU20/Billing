import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { typography, radius } from '@/constants/tokens'
import type { AuthUser } from '@/features/auth/types'
import { getUserInitial } from '@/features/auth/utils/userDisplay'

interface UserAvatarProps {
  user: AuthUser
  size?: 'sm' | 'lg'
}

export function UserAvatar({ user, size = 'sm' }: UserAvatarProps) {
  const { semantic } = useTheme()

  return (
    <View style={[styles.avatar, size === 'lg' && styles.avatarLg, { backgroundColor: semantic.accent.default }]}>
      <Text style={[styles.avatarText, size === 'lg' && styles.avatarTextLg, { color: semantic.text.onDark }]}>
        {getUserInitial(user)}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  avatar: { width: 32, height: 32, borderRadius: radius.full, alignItems: 'center', justifyContent: 'center' },
  avatarLg: { width: 44, height: 44 },
  avatarText: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  avatarTextLg: { fontSize: typography.size.md },
})
