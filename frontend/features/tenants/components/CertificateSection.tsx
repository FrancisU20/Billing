import React, { useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
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
}

export function CertificateSection({ tenantId, canManage }: CertificateSectionProps) {
  const { semantic } = useTheme()
  const toast = useToast()
  const { certificate, loading, error, refresh } = useTenantCertificate(tenantId)
  const [replacing, setReplacing] = useState(false)
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
  })

  if (loading && !certificate) {
    return (
      <DetailSection title="Certificado digital" icon="ribbon-outline" layout="stack">
        <LoadingSpinner size="small" compact />
      </DetailSection>
    )
  }

  if (error) {
    return (
      <DetailSection title="Certificado digital" icon="ribbon-outline" layout="stack">
        <ApiErrorBanner error={error} />
        <Button variant="outline" size="sm" onPress={refresh}>
          Reintentar
        </Button>
      </DetailSection>
    )
  }

  const hasCertificate = !!certificate?.cert_expires_at
  const status =
    hasCertificate && certificate?.cert_expires_at ? expiryBadge(certificate.cert_expires_at) : null

  return (
    <DetailSection title="Certificado digital" icon="ribbon-outline" layout="stack">
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
                  setReplacing(false)
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
          <Button variant="outline" size="sm" onPress={() => setReplacing(true)}>
            {hasCertificate ? 'Reemplazar certificado' : 'Subir certificado'}
          </Button>
        )
      ) : null}
    </DetailSection>
  )
}

const styles = StyleSheet.create({
  message: { fontSize: typography.size.base, lineHeight: typography.size.base * 1.5 },
  form: { gap: spacing[4] },
  actions: { flexDirection: 'row', gap: spacing[2] },
})
