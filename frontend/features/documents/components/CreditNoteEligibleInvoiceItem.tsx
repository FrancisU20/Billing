import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Button } from '@/components/ui/Button'
import { ListCell, ListItemMeta } from '@/components/ui/ListItemPrimitives'
import { useIsDesktopLayout } from '@/lib/hooks/useIsDesktopLayout'
import { useTheme } from '@/lib/theme-context'
import { formatDate } from '@/lib/utils/format'
import { radius, spacing, typography } from '@/constants/tokens'
import type { Document } from '../types'

interface CreditNoteEligibleInvoiceItemProps {
  document: Document
  canCreate: boolean
  onPress: () => void
}

/** Fila del modulo independiente "Notas de Credito" — lista solo facturas (doc_type
 * 01, status AUTHORIZED, ya filtradas por el caller) con un unico boton "Acreditar"
 * que navega al formulario parcial existente. A diferencia de DocumentListItem (usado
 * en Documentos), no hay acciones de ver/descargar/anular: este modulo solo crea
 * notas de credito. */
export function CreditNoteEligibleInvoiceItem({
  document,
  canCreate,
  onPress,
}: CreditNoteEligibleInvoiceItemProps) {
  const { semantic } = useTheme()
  const isDesktop = useIsDesktopLayout()

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
      <Button variant="outline" size="sm" isDisabled={!canCreate} onPress={onPress}>
        Acreditar
      </Button>
    </View>
  )
}

function MobileRow({ document }: { document: Document }) {
  const { semantic } = useTheme()
  return (
    <>
      <Text style={[styles.sequential, { color: semantic.text.primary }]} numberOfLines={1}>
        {document.sequential_display}
      </Text>
      <Text style={[styles.buyer, { color: semantic.text.secondary }]} numberOfLines={1}>
        {document.buyer_name}
      </Text>
      <View style={styles.metaRow}>
        <ListItemMeta icon="calendar-outline" text={formatDate(document.issued_at)} />
        <ListItemMeta icon="cash-outline" text={`$${document.total}`} />
      </View>
    </>
  )
}

function DesktopRow({ document }: { document: Document }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.desktopRow}>
      <View style={styles.colDoc}>
        <Text style={[styles.sequential, { color: semantic.text.primary }]} numberOfLines={1}>
          {document.sequential_display}
        </Text>
        <Text style={[styles.buyer, { color: semantic.text.secondary }]} numberOfLines={1}>
          {document.buyer_name}
        </Text>
      </View>
      <ListCell label="Fecha" value={formatDate(document.issued_at)} style={styles.colDate} />
      <ListCell label="Total" value={`$${document.total}`} style={styles.colTotal} />
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
  sequential: {
    fontFamily: typography.fontFamily.mono,
    fontSize: typography.size.base,
    fontWeight: typography.weight.bold,
  },
  buyer: { fontSize: typography.size.sm },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  desktopRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[5] },
  colDoc: { flexBasis: 260, gap: spacing[1], minWidth: 200 },
  colDate: { flexBasis: 120 },
  colTotal: { flexBasis: 110 },
})
