import React, { useState } from 'react'
import { StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { CertificateUploadField } from '@/components/ui/CertificateUploadField'
import { DetailField, DetailSection } from '@/components/ui/DetailSection'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useCertificateFilePicker } from '@/lib/hooks/useCertificateFilePicker'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { formatDate, formatDateTime, formatRuc } from '@/lib/utils/format'
import { spacing, typography } from '@/constants/tokens'
import { tenantsApi } from '../api'
import {
  CERTIFICATE_EXPIRY_DANGER_DAYS,
  CERTIFICATE_EXPIRY_WARNING_DAYS,
  MILLISECONDS_PER_DAY,
} from '../constants'
import { useTenantCertificate } from '../hooks/useTenantCertificate'

type ExpiryVariant = 'success' | 'warning' | 'error'

function expiryBadge(expiresAt: string): { label: string; variant: ExpiryVariant } {
  const daysLeft = Math.ceil((new Date(expiresAt).getTime() - Date.now()) / MILLISECONDS_PER_DAY)
  if (daysLeft < 0) return { label: 'Vencido', variant: 'error' }
  if (daysLeft <= CERTIFICATE_EXPIRY_DANGER_DAYS)
    return { label: `Vence en ${daysLeft} días`, variant: 'error' }
  if (daysLeft <= CERTIFICATE_EXPIRY_WARNING_DAYS)
    return { label: `Vence en ${daysLeft} días`, variant: 'warning' }
  return { label: 'Vigente', variant: 'success' }
}

interface CertificateSectionProps {
  tenantId: string
  canManage: boolean
  style?: StyleProp<ViewStyle>
  actionSize?: 'sm' | 'md'
  startEditing?: boolean
  onUploaded?: () => void
}

export function CertificateSection({
  tenantId,
  canManage,
  style,
  actionSize = 'sm',
  startEditing = false,
  onUploaded,
}: CertificateSectionProps) {
  const { semantic } = useTheme()
  const toast = useToast()
  const { certificate, loading, error, refresh } = useTenantCertificate(tenantId)
  const [replacing, setReplacing] = useState(startEditing)
  const {
    fileName,
    certificateB64,
    error: pickerError,
    pickFile,
    reset: resetPicker,
  } = useCertificateFilePicker()
  const [certPassword, setCertPassword] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const {
    submitting,
    error: submitError,
    submit,
  } = useFormSubmit(async () => {
    if (!fileName || !certificateB64) {
      setLocalError('Selecciona tu certificado p12.')
      return
    }
    if (!certPassword.trim()) {
      setLocalError('Ingresa la clave del certificado.')
      return
    }
    setLocalError(null)

    await tenantsApi.replaceCertificate(
      tenantId,
      { certificate_b64: certificateB64, cert_password: certPassword },
      createIdempotencyKey('certificate_replace'),
    )
    toast.success('Certificado actualizado')
    setReplacing(false)
    setCertPassword('')
    resetPicker()
    await refresh()
    onUploaded?.()
  })

  if (loading && !certificate) {
    return (
      <DetailSection
        title="Certificado digital"
        icon="ribbon-outline"
        layout="stack"
        style={style}
        contentStyle={styles.loadingBody}
      >
        <LoadingSpinner size="small" compact />
      </DetailSection>
    )
  }

  if (error) {
    return (
      <DetailSection
        title="Certificado digital"
        icon="ribbon-outline"
        layout="stack"
        style={style}
        contentStyle={styles.sectionBody}
      >
        <ApiErrorBanner error={error} />
        <View style={styles.actionFooter}>
          <Button variant="outline" size="sm" onPress={refresh}>
            Reintentar
          </Button>
        </View>
      </DetailSection>
    )
  }

  const hasCertificate = !!certificate?.cert_expires_at
  const status =
    hasCertificate && certificate?.cert_expires_at ? expiryBadge(certificate.cert_expires_at) : null

  return (
    <DetailSection
      title="Certificado digital"
      icon="ribbon-outline"
      layout="stack"
      style={style}
      contentStyle={styles.sectionBody}
    >
      <View style={styles.details}>
        {hasCertificate && certificate ? (
          <>
            {status ? <Badge label={status.label} variant={status.variant} /> : null}
            <DetailField
              label="RUC titular"
              value={certificate.cert_subject_ruc ? formatRuc(certificate.cert_subject_ruc) : '-'}
              mono
            />
            <DetailField label="Emisor" value={certificate.cert_issuer ?? '-'} />
            <DetailField
              label="Vence el"
              value={certificate.cert_expires_at ? formatDate(certificate.cert_expires_at) : '-'}
            />
            <DetailField
              label="Subido el"
              value={
                certificate.cert_uploaded_at ? formatDateTime(certificate.cert_uploaded_at) : '-'
              }
            />
          </>
        ) : (
          <Text style={[styles.message, { color: semantic.text.secondary }]}>
            Aún no se ha registrado un certificado digital.
          </Text>
        )}
      </View>

      {canManage ? (
        replacing ? (
          <View style={styles.form}>
            <CertificateUploadField
              fileName={fileName}
              certPassword={certPassword}
              onChangeCertPassword={setCertPassword}
              onPickFile={pickFile}
              errorMessage={localError ?? pickerError}
            />
            {submitError ? <ApiErrorBanner error={submitError} /> : null}

            <View style={styles.actions}>
              <Button variant="primary" size="md" isLoading={submitting} onPress={submit}>
                Guardar
              </Button>
              <Button
                variant="outline"
                size="md"
                isDisabled={submitting}
                onPress={() => {
                  if (!startEditing) setReplacing(false)
                  setLocalError(null)
                  setCertPassword('')
                  resetPicker()
                }}
              >
                Cancelar
              </Button>
            </View>
          </View>
        ) : (
          <View style={styles.actionFooter}>
            <Button
              variant="outline"
              size={actionSize}
              fullWidth
              onPress={() => setReplacing(true)}
            >
              {hasCertificate ? 'Reemplazar certificado' : 'Subir certificado'}
            </Button>
          </View>
        )
      ) : null}
    </DetailSection>
  )
}

const styles = StyleSheet.create({
  sectionBody: { flex: 1 },
  // minHeight aproxima el alto del estado cargado (badge + 4 DetailField) para que el
  // card no se vea mas chico mientras el spinner esta solo, y no "salte" de tamano al
  // terminar de cargar.
  loadingBody: { flex: 1, minHeight: 220, alignItems: 'center', justifyContent: 'center' },
  details: { gap: spacing[4] },
  message: { fontSize: typography.size.base, lineHeight: typography.size.base * 1.5 },
  actionFooter: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 'auto',
    width: '100%',
  },
  form: { gap: spacing[4], marginTop: 'auto' },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2], justifyContent: 'center' },
})
