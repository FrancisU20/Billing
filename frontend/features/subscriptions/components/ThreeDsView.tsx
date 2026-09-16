import React from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { radius, shadow, spacing, typography } from '@/constants/tokens'
import { useTheme } from '@/lib/theme-context'

interface AwaitingProps {
  checking: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ThreeDsAwaitingView({ checking, onConfirm, onCancel }: AwaitingProps) {
  const { semantic } = useTheme()
  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View
          style={[
            styles.card,
            { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
          ]}
        >
          <View style={styles.cardHeader}>
            <View style={[styles.iconWrap, { backgroundColor: semantic.accent.subtle }]}>
              <Ionicons name="shield-checkmark-outline" size={22} color={semantic.accent.default} />
            </View>
            <View style={styles.cardTitle}>
              <Text style={[styles.title, { color: semantic.text.primary }]}>
                Verificación del banco
              </Text>
              <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
                Tu banco requiere autenticación adicional. Completa la verificación en la pestaña
                que se abrió y luego regresa aquí.
              </Text>
            </View>
          </View>
          <View style={[styles.divider, { backgroundColor: semantic.border.default }]} />
          <Button variant="primary" size="lg" fullWidth isLoading={checking} onPress={onConfirm}>
            Ya completé la verificación
          </Button>
          <Button variant="ghost" size="sm" fullWidth onPress={onCancel}>
            Cancelar
          </Button>
        </View>
      </ScrollView>
    </View>
  )
}

interface FailedProps {
  error: string
  onRetry: () => void
}

export function ThreeDsFailedView({ error, onRetry }: FailedProps) {
  const { semantic } = useTheme()
  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View
          style={[
            styles.card,
            { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
          ]}
        >
          <View
            style={[
              styles.infoBox,
              { backgroundColor: semantic.status.errorBg, borderColor: semantic.status.error },
            ]}
          >
            <Ionicons name="alert-circle-outline" size={16} color={semantic.status.error} />
            <Text style={[styles.infoText, { color: semantic.status.error }]}>{error}</Text>
          </View>
          <Button variant="primary" size="lg" fullWidth onPress={onRetry}>
            Intentar de nuevo
          </Button>
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], gap: spacing[5], paddingBottom: spacing[12] },
  card: {
    borderRadius: radius.md,
    borderWidth: 1,
    padding: spacing[5],
    gap: spacing[4],
    ...shadow.md,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing[3] },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  cardTitle: { flex: 1, gap: spacing[1] },
  title: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  subtitle: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
  divider: { height: 1 },
  infoBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing[2],
    padding: spacing[3],
    borderRadius: radius.sm,
    borderWidth: 1,
  },
  infoText: {
    flex: 1,
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
})
