import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing, radius } from '@/constants/tokens'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { useLogout } from '@/features/auth/hooks/useLogout'
import { getUserAccessLabel, getUserInitial, getUserRoleLabel } from '../utils/userDisplay'

export function ProfileScreen() {
  const user = useAuthStore(selectUser)
  const { semantic } = useTheme()
  const { logout, loading } = useLogout()
  const roleLabel = getUserRoleLabel(user)
  const initial = getUserInitial(user)

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Mi perfil" subtitle="Cuenta" />

      <View style={styles.content}>
        <Card variant="elevated" elevated style={styles.profileCard}>
          <View style={styles.header}>
            <View style={[styles.avatar, { backgroundColor: semantic.accent.default }]}>
              <Text style={[styles.avatarText, { color: semantic.text.onDark }]}>{initial}</Text>
            </View>
            <View style={styles.identity}>
              <Text style={[styles.email, { color: semantic.text.primary }]} numberOfLines={1}>
                {user?.email}
              </Text>
              <Badge label={roleLabel} variant="primary" size="sm" />
            </View>
          </View>

          <View style={[styles.divider, { backgroundColor: semantic.border.default }]} />

          <ProfileRow icon="person-circle-outline" label="Rol" value={roleLabel} />
          <ProfileRow icon="business-outline" label="Tenant" value={user?.tenantId ?? 'No asignado'} />
          <ProfileRow icon="shield-checkmark-outline" label="Acceso" value={getUserAccessLabel(user)} />

          <Button variant="outline" size="md" onPress={logout} isLoading={loading} style={styles.logoutButton as any}>
            Cerrar sesión
          </Button>
        </Card>
      </View>
    </View>
  )
}

function ProfileRow({ icon, label, value }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string }) {
  const { semantic } = useTheme()

  return (
    <View style={styles.row}>
      <View style={[styles.rowIcon, { backgroundColor: semantic.bg.muted }]}>
        <Ionicons name={icon} size={18} color={semantic.text.secondary} />
      </View>
      <View style={styles.rowCopy}>
        <Text style={[styles.rowLabel, { color: semantic.text.secondary }]}>{label}</Text>
        <Text style={[styles.rowValue, { color: semantic.text.primary }]} numberOfLines={1}>{value}</Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: spacing[5] },
  profileCard: { gap: spacing[4] },
  header: { flexDirection: 'row', alignItems: 'center', gap: spacing[4] },
  avatar: { width: 64, height: 64, borderRadius: radius.full, alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: typography.size['2xl'], fontWeight: typography.weight.bold },
  identity: { flex: 1, minWidth: 0, gap: spacing[2] },
  email: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  divider: { height: 1 },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  rowIcon: { width: 40, height: 40, borderRadius: radius.lg, alignItems: 'center', justifyContent: 'center' },
  rowCopy: { flex: 1, minWidth: 0, gap: spacing[1] },
  rowLabel: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  rowValue: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  logoutButton: { marginTop: spacing[2] },
})
