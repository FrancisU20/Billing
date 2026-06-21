import React, { useEffect, useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { CertificateUploadField } from '@/components/ui/CertificateUploadField'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'
import { useCertificateFilePicker } from '@/lib/hooks/useCertificateFilePicker'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { formValuesToOnboardingPayload } from '../form'
import { useRequestOtp } from '../hooks/useRequestOtp'
import { useOnboardingStore } from '../store'

export function RegisterCertificateScreen() {
  const { semantic } = useTheme()
  const router = useRouter()
  const selectedPlan = useOnboardingStore((state) => state.selectedPlan)
  const selectedBillingCycle = useOnboardingStore((state) => state.selectedBillingCycle)
  const formValues = useOnboardingStore((state) => state.formValues)
  const certificateValues = useOnboardingStore((state) => state.certificateValues)
  const setCertificateValues = useOnboardingStore((state) => state.setCertificateValues)
  const requestOtp = useRequestOtp()
  const {
    fileName,
    certificateB64,
    error: pickerError,
    pickFile,
  } = useCertificateFilePicker({
    fileName: certificateValues?.file_name,
    certificateB64: certificateValues?.certificate_b64,
  })
  const [certPassword, setCertPassword] = useState(certificateValues?.cert_password ?? '')
  const [localError, setLocalError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedPlan || !formValues) {
      router.replace(Routes.root as Href)
      return
    }
    if (!selectedPlan.self_service) {
      router.replace(Routes.public.registerOtp as Href)
    }
  }, [formValues, selectedPlan, router])

  const { submitting, error, submit } = useFormSubmit(async () => {
    if (!selectedPlan || !formValues) return
    if (!fileName || !certificateB64) {
      setLocalError('Selecciona tu certificado p12.')
      return
    }
    if (!certPassword.trim()) {
      setLocalError('Ingresa la clave del certificado.')
      return
    }

    const certificate = {
      file_name: fileName,
      certificate_b64: certificateB64,
      cert_password: certPassword,
    }
    setCertificateValues(certificate)
    await requestOtp({
      ...formValuesToOnboardingPayload(formValues, selectedPlan.id, selectedBillingCycle),
      certificate_b64: certificate.certificate_b64,
      cert_password: certificate.cert_password,
    })
  })

  if (!selectedPlan || !formValues) return null

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: semantic.text.primary }]}>Certificado digital</Text>
        <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
          Validaremos que el p12 pertenezca al RUC registrado y esté vigente.
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View
          style={[
            styles.section,
            { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
          ]}
        >
          <CertificateUploadField
            fileName={fileName}
            certPassword={certPassword}
            onChangeCertPassword={setCertPassword}
            onPickFile={pickFile}
            errorMessage={localError ?? pickerError}
          />
          {error ? <ApiErrorBanner error={error} /> : null}

          <Button variant="primary" size="lg" fullWidth isLoading={submitting} onPress={submit}>
            Enviar código
          </Button>
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { gap: spacing[2], padding: spacing[5], paddingTop: spacing[8] },
  title: {
    fontSize: typography.size['3xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['3xl'] * typography.lineHeight.tight,
  },
  subtitle: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.normal,
  },
  scroll: { padding: spacing[5], paddingBottom: spacing[12] },
  section: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    padding: spacing[4],
  },
})
