import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { ListItemAction, ListItemMeta } from '@/components/ui/ListItemPrimitives'
import { useTheme } from '@/lib/theme-context'
import { formatDate } from '@/lib/utils/format'
import { radius, spacing, typography } from '@/constants/tokens'
import { DocumentStatusBadge } from './DocumentStatusBadge'
import type { Document } from '../types'

interface DocumentListItemProps {
  document: Document
  onView: () => void
}

export function DocumentListItem({ document, onView }: DocumentListItemProps) {
  const { semantic } = useTheme()
  return (
    <Pressable
      onPress={onView}
      style={({ pressed }) => [
        styles.container,
        {
          backgroundColor: pressed ? semantic.bg.secondary : semantic.bg.card,
          borderColor: semantic.border.default,
        },
      ]}
    >
      <View style={styles.main}>
        <View style={styles.nameRow}>
          <Text style={[styles.sequential, { color: semantic.text.primary }]} numberOfLines={1}>
            {document.sequential_display}
          </Text>
          <DocumentStatusBadge status={document.status} />
        </View>
        <Text style={[styles.buyer, { color: semantic.text.secondary }]} numberOfLines={1}>
          {document.buyer_name}
        </Text>
        <View style={styles.metaRow}>
          <ListItemMeta icon="calendar-outline" text={formatDate(document.issued_at)} />
          <ListItemMeta icon="cash-outline" text={`$${document.total}`} />
          <ListItemMeta icon="key-outline" text={document.access_key} mono />
        </View>
      </View>
      <View style={styles.actions}>
        <ListItemAction icon="eye-outline" label="Ver documento" onPress={onView} />
      </View>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    padding: spacing[4],
  },
  main: { flex: 1, gap: spacing[1], minWidth: 0 },
  nameRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  sequential: {
    flex: 1,
    fontFamily: typography.fontFamily.mono,
    fontSize: typography.size.base,
    fontWeight: typography.weight.bold,
  },
  buyer: { fontSize: typography.size.sm },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  actions: { flexDirection: 'row', gap: spacing[2] },
})
