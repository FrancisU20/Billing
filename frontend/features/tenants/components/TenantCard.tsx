import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { typography, radius, spacing } from '@/constants/tokens'
import { formatRuc, initials } from '@/lib/utils/format'
import { TenantStatusBadge } from './TenantStatusBadge'
import type { Tenant } from '../types'

interface TenantCardProps {
  tenant: Tenant
  onPress?: () => void
}

export function TenantCard({ tenant, onPress }: TenantCardProps) {
  const { semantic } = useTheme()

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        staticStyles.container,
        {
          backgroundColor: pressed ? semantic.bg.secondary : semantic.bg.card,
          borderColor: semantic.border.default,
        },
      ]}
    >
      <View style={[staticStyles.avatar, { backgroundColor: semantic.accent.subtle }]}>
        <Text style={[staticStyles.avatarText, { color: semantic.accent.default }]}>
          {initials(tenant.trade_name)}
        </Text>
      </View>

      <View style={staticStyles.body}>
        <Text style={[staticStyles.name, { color: semantic.text.primary }]} numberOfLines={1}>
          {tenant.trade_name}
        </Text>
        <Text style={[staticStyles.ruc, { color: semantic.text.secondary }]}>
          {formatRuc(tenant.ruc)}
        </Text>
        <View style={staticStyles.row}>
          <Ionicons name="mail-outline" size={12} color={semantic.text.tertiary} />
          <Text style={[staticStyles.email, { color: semantic.text.tertiary }]} numberOfLines={1}>
            {tenant.email}
          </Text>
        </View>
      </View>

      <View style={staticStyles.right}>
        <TenantStatusBadge status={tenant.status} />
        <Ionicons name="chevron-forward" size={16} color={semantic.text.tertiary} />
      </View>
    </Pressable>
  )
}

const staticStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    borderRadius: radius.xl,
    borderWidth: 1,
    padding: spacing[4],
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  body: { flex: 1, gap: 3 },
  name: { fontSize: typography.size.base, fontWeight: typography.weight.semibold },
  ruc: { fontSize: typography.size.xs, fontFamily: 'Courier' },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing[1] },
  email: { fontSize: typography.size.xs, flex: 1 },
  right: { alignItems: 'flex-end', gap: spacing[2] },
})
