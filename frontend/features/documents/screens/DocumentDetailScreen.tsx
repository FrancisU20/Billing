import React, { useState } from 'react'
import { Linking, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useLocalSearchParams } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { DetailField, DetailSection } from '@/components/ui/DetailSection'
import { EmptyState } from '@/components/ui/EmptyState'
import { FormField } from '@/components/ui/FormField'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { formatDate, formatDateTime } from '@/lib/utils/format'
import { useTheme } from '@/lib/theme-context'
import { canWrite } from '@/constants/roles'
import { radius, spacing, typography } from '@/constants/tokens'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { documentsApi } from '../api'
import { DocumentLineSummaryRow } from '../components/DocumentLineSummaryRow'
import { DocumentStatusBadge } from '../components/DocumentStatusBadge'
import { TotalsSummary } from '../components/TotalsSummary'
import { BUYER_ID_TYPE_LABELS, CONSUMIDOR_FINAL_ID_TYPE } from '../constants'
import { useDocument } from '../hooks/useDocument'
import { isWithinAnnulmentWindow } from '../utils'

export function DocumentDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { semantic } = useTheme()
  const toast = useToast()
  const user = useAuthStore(selectUser)
  const { document, loading, error, refresh } = useDocument(id ?? null)
  const [annulling, setAnnulling] = useState(false)
  const [reason, setReason] = useState('')
  const [reasonError, setReasonError] = useState<string | null>(null)

  useRefreshOnFocus(refresh)

  const {
    submitting: downloading,
    error: downloadError,
    submit: downloadRide,
  } = useFormSubmit(async () => {
    if (!id) return
    const { url } = await documentsApi.getRideUrl(id)
    await Linking.openURL(url)
  })
  const {
    submitting: downloadingXml,
    error: downloadXmlError,
    submit: downloadXml,
  } = useFormSubmit(async () => {
    if (!id) return
    const { url } = await documentsApi.getXmlUrl(id)
    await Linking.openURL(url)
  })

  const {
    submitting: annullingSubmit,
    error: annulError,
    submit: confirmAnnul,
  } = useFormSubmit(async () => {
    if (!id) return
    if (!reason.trim()) {
      setReasonError('Indica el motivo de la anulación.')
      return
    }
    setReasonError(null)
    await documentsApi.annul(id, reason.trim(), createIdempotencyKey('document_annul'))
    toast.success('Documento marcado como anulado')
    setAnnulling(false)
    setReason('')
    await refresh()
  })

  const canAnnul =
    !!document &&
    canWrite(user?.role ?? null) &&
    document.status === 'AUTHORIZED' &&
    document.buyer_id_type !== CONSUMIDOR_FINAL_ID_TYPE &&
    isWithinAnnulmentWindow(document.issued_at)

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
              <View style={styles.profileActions}>
                {document.ride_s3_key ? (
                    <Button
                      variant="outline"
                      size="sm"
                      isLoading={downloading}
                      onPress={() => downloadRide()}
                    >
                      Descargar RIDE
                    </Button>
                ) : null}
                {document.xml_s3_key ? (
                  <Button
                    variant="outline"
                    size="sm"
                    isLoading={downloadingXml}
                    onPress={() => downloadXml()}
                  >
                    Descargar XML
                  </Button>
                ) : null}
                {canAnnul ? (
                  <Button variant="danger" size="sm" onPress={() => setAnnulling(true)}>
                    Anular factura
                  </Button>
                ) : null}
              </View>
            </View>

            {downloadError ? <ApiErrorBanner error={downloadError} /> : null}
            {downloadXmlError ? <ApiErrorBanner error={downloadXmlError} /> : null}

            {document.status === 'ANNULLED' ? (
              <View
                style={[
                  styles.infoBanner,
                  { backgroundColor: semantic.bg.muted, borderColor: semantic.border.default },
                ]}
              >
                <Text style={[styles.infoBannerText, { color: semantic.text.secondary }]}>
                  Anulado{document.annulled_at ? ` el ${formatDateTime(document.annulled_at)}` : ''}
                  {document.annulment_reason ? ` — ${document.annulment_reason}` : ''}
                </Text>
              </View>
            ) : null}

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
                    {e.code}: {e.user_message ?? e.message}
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

            <DetailSection title="Productos" icon="list-outline" layout="stack">
              <View style={styles.linesList}>
                {document.lines.map((line, index) => (
                  <DocumentLineSummaryRow key={`${line.code}-${index}`} line={line} />
                ))}
              </View>
            </DetailSection>

            <TotalsSummary
              subtotal={Number(document.subtotal)}
              totalDiscount={Number(document.total_discount)}
              iva15={Number(document.iva_15)}
              iva5={Number(document.iva_5)}
              total={Number(document.total)}
            />
          </>
        ) : null}
      </ScrollView>

      <ConfirmDialog
        visible={annulling}
        title="Anular factura"
        message="Esta acción no se puede revertir. El trámite de anulación ante el SRI se hace por fuera de Wali (portal SRI en línea o Facturador SRI) — marca esto como anulado solo después de completarlo ahí."
        confirmLabel="Marcar como anulado"
        variant="danger"
        icon="ban-outline"
        isLoading={annullingSubmit}
        confirmDisabled={!reason.trim()}
        onCancel={() => {
          setAnnulling(false)
          setReason('')
          setReasonError(null)
        }}
        onConfirm={() => confirmAnnul()}
      >
        <FormField
          label="Motivo de la anulación"
          placeholder="Ej. error en el monto facturado"
          leftIcon="alert-circle-outline"
          error={reasonError ?? undefined}
          onChangeText={(value) => {
            setReason(value)
            setReasonError(null)
          }}
          value={reason}
          required
        />
        {annulError ? <ApiErrorBanner error={annulError} /> : null}
      </ConfirmDialog>
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
  linesList: { gap: spacing[2] },
  profileActions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
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
