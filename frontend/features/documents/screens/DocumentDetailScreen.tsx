import React from 'react'
import { Linking, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useLocalSearchParams } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { DetailField, DetailSection } from '@/components/ui/DetailSection'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { formatDate, formatDateTime } from '@/lib/utils/format'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { documentsApi } from '../api'
import { DocumentStatusBadge } from '../components/DocumentStatusBadge'
import { BUYER_ID_TYPE_LABELS } from '../constants'
import { useDocument } from '../hooks/useDocument'

export function DocumentDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { semantic } = useTheme()
  const { document, loading, error, refresh } = useDocument(id ?? null)

  const {
    submitting: downloading,
    error: downloadError,
    submit: downloadRide,
  } = useFormSubmit(async () => {
    if (!id) return
    const { url } = await documentsApi.getRideUrl(id)
    await Linking.openURL(url)
  })

  if (loading) return <LoadingSpinner fullScreen label="Cargando documento..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title={document?.sequential_display ?? 'Documento'} canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {error ? (
          <EmptyState
            icon="alert-circle-outline"
            title="No se pudo cargar el documento"
            description={error.message}
            action={{ label: 'Reintentar', onPress: refresh }}
          />
        ) : document ? (
          <>
            <View
              style={[
                styles.profile,
                { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
              ]}
            >
              <View style={styles.profileCopy}>
                <Text style={[styles.sequential, { color: semantic.text.primary }]}>
                  {document.sequential_display}
                </Text>
                <Text
                  style={[styles.accessKey, { color: semantic.text.secondary }]}
                  numberOfLines={2}
                >
                  {document.access_key}
                </Text>
                <View style={styles.badgeRow}>
                  <DocumentStatusBadge status={document.status} />
                </View>
              </View>
              {document.status === 'AUTHORIZED' ? (
                <Button
                  variant="outline"
                  size="sm"
                  isLoading={downloading}
                  onPress={() => downloadRide()}
                >
                  Descargar RIDE
                </Button>
              ) : null}
            </View>

            {downloadError ? <ApiErrorBanner error={downloadError} /> : null}

            {document.status === 'PENDING' || document.status === 'PROCESSING' ? (
              <View
                style={[
                  styles.infoBanner,
                  { backgroundColor: semantic.accent.subtle, borderColor: semantic.accent.default },
                ]}
              >
                <Text style={[styles.infoBannerText, { color: semantic.accent.default }]}>
                  Esperando autorización del SRI — esta pantalla se actualiza automáticamente.
                </Text>
              </View>
            ) : null}

            {document.sri_errors && document.sri_errors.length > 0 ? (
              <View
                style={[
                  styles.infoBanner,
                  { backgroundColor: semantic.status.errorBg, borderColor: semantic.status.error },
                ]}
              >
                {document.sri_errors.map((e, i) => (
                  <Text
                    key={`${e.code}-${i}`}
                    style={[styles.infoBannerText, { color: semantic.status.error }]}
                  >
                    {e.code}: {e.message}
                  </Text>
                ))}
              </View>
            ) : null}

            <DetailSection title="Datos tributarios" icon="document-text-outline">
              <DetailField label="Serie" value={document.serie} mono />
              <DetailField label="Ambiente" value={document.sri_environment} />
              <DetailField label="Fecha de emisión" value={formatDate(document.issued_at)} />
              <DetailField label="Forma de pago" value={document.payment_method} />
              {document.authorization_number ? (
                <DetailField
                  label="N° de autorización"
                  value={document.authorization_number}
                  mono
                />
              ) : null}
              {document.authorized_at ? (
                <DetailField
                  label="Fecha de autorización"
                  value={formatDateTime(document.authorized_at)}
                />
              ) : null}
            </DetailSection>

            <DetailSection title="Comprador" icon="person-outline">
              <DetailField
                label={BUYER_ID_TYPE_LABELS[document.buyer_id_type]}
                value={document.buyer_id}
                mono
              />
              <DetailField label="Nombre" value={document.buyer_name} />
              <DetailField label="Email" value={document.buyer_email ?? 'Sin email'} />
            </DetailSection>

            <DetailSection title="Líneas de detalle" icon="list-outline">
              {document.lines.map((line, index) => (
                <DetailField
                  key={`${line.code}-${index}`}
                  label={`${line.code} · ${line.description}`}
                  value={`${line.quantity} × $${line.unit_price} = $${line.total} (IVA ${line.iva_rate === 'EXENTO' ? 'Exento' : `${line.iva_rate}%`})`}
                />
              ))}
            </DetailSection>

            <DetailSection title="Totales" icon="cash-outline">
              <DetailField label="Subtotal" value={`$${document.subtotal}`} />
              <DetailField label="Descuento" value={`$${document.total_discount}`} />
              <DetailField label="IVA 15%" value={`$${document.iva_15}`} />
              <DetailField label="IVA 5%" value={`$${document.iva_5}`} />
              <DetailField label="Total" value={`$${document.total}`} />
            </DetailSection>
          </>
        ) : null}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
  profile: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[4],
    padding: spacing[5],
  },
  profileCopy: { flex: 1, gap: spacing[1], minWidth: 220 },
  sequential: {
    fontFamily: typography.fontFamily.mono,
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
  },
  accessKey: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.xs },
  badgeRow: { flexDirection: 'row', gap: spacing[2], marginTop: spacing[1] },
  infoBanner: { borderLeftWidth: 3, borderRadius: radius.md, gap: spacing[1], padding: spacing[3] },
  infoBannerText: { fontSize: typography.size.sm, lineHeight: typography.size.sm * 1.5 },
})
