import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Badge } from '@/components/ui/Badge'
import { ListCell, ListItemAction, ListItemMeta } from '@/components/ui/ListItemPrimitives'
import { RowActionsMenu, type RowAction } from '@/components/ui/RowActionsMenu'
import { useIsDesktopLayout } from '@/lib/hooks/useIsDesktopLayout'
import { useTheme } from '@/lib/theme-context'
import { formatDate } from '@/lib/utils/format'
import { radius, spacing, typography } from '@/constants/tokens'
import { DOC_TYPE_LABELS } from '../constants'
import { DocumentStatusBadge } from './DocumentStatusBadge'
import type { Document } from '../types'

interface DocumentListItemProps {
  document: Document
  onView: () => void
  onDownloadRide: () => void
  onDownloadXml: () => void
  onAnnul?: () => void
  canAnnul?: boolean
  annulDisabledReason?: string | null
}

export function DocumentListItem({
  document,
  onView,
  onDownloadRide,
  onDownloadXml,
  onAnnul,
  canAnnul = false,
  annulDisabledReason = null,
}: DocumentListItemProps) {
  const { semantic } = useTheme()
  const isDesktop = useIsDesktopLayout()

  const rowActions: RowAction[] = [
    ...(document.ride_s3_key
      ? [
          {
            key: 'download-ride',
            icon: 'download-outline' as const,
            label: 'Descargar RIDE',
            onPress: onDownloadRide,
          },
        ]
      : []),
    ...(document.xml_s3_key
      ? [
          {
            key: 'download-xml',
            icon: 'code-download-outline' as const,
            label: 'Descargar XML',
            onPress: onDownloadXml,
          },
        ]
      : []),
    ...(canAnnul && onAnnul
      ? [
          {
            key: 'annul-document',
            icon: 'ban-outline' as const,
            label: 'Anular factura',
            danger: true,
            disabled: Boolean(annulDisabledReason),
            disabledReason: annulDisabledReason ?? undefined,
            onPress: onAnnul,
          },
        ]
      : []),
  ]

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.main}>
        {isDesktop ? <DesktopRow document={document} /> : <MobileRow document={document} />}
      </View>
      <View style={styles.actions}>
        <ListItemAction icon="eye-outline" label="Ver documento" onPress={onView} />
        <RowActionsMenu actions={rowActions} triggerLabel="Más acciones de documento" />
      </View>
    </View>
  )
}

function MobileRow({ document }: { document: Document }) {
  const { semantic } = useTheme()
  return (
    <>
      <View style={styles.nameRow}>
        <Text style={[styles.sequential, { color: semantic.text.primary }]} numberOfLines={1}>
          {document.sequential_display}
        </Text>
        {document.doc_type !== '01' ? (
          <Badge
            label={DOC_TYPE_LABELS[document.doc_type] ?? document.doc_type}
            variant="neutral"
            size="sm"
          />
        ) : null}
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
    </>
  )
}

function DesktopRow({ document }: { document: Document }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.desktopRow}>
      <View style={styles.colDoc}>
        <View style={styles.nameRow}>
          <Text style={[styles.sequential, { color: semantic.text.primary }]} numberOfLines={1}>
            {document.sequential_display}
          </Text>
          {document.doc_type !== '01' ? (
            <Badge
              label={DOC_TYPE_LABELS[document.doc_type] ?? document.doc_type}
              variant="neutral"
              size="sm"
            />
          ) : null}
          <DocumentStatusBadge status={document.status} />
        </View>
        <Text style={[styles.buyer, { color: semantic.text.secondary }]} numberOfLines={1}>
          {document.buyer_name}
        </Text>
      </View>
      <ListCell label="Fecha" value={formatDate(document.issued_at)} style={styles.colDate} />
      <ListCell label="Total" value={`$${document.total}`} style={styles.colTotal} />
      <ListCell label="Clave de acceso" value={document.access_key} mono style={styles.colKey} />
    </View>
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
  desktopRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[5] },
  colDoc: { flexBasis: 260, gap: spacing[1], minWidth: 200 },
  colDate: { flexBasis: 120 },
  colTotal: { flexBasis: 110 },
  colKey: { flex: 1, minWidth: 200 },
})
