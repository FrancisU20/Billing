import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { radius, spacing, typography } from '@/constants/tokens'
import { useTheme } from '@/lib/theme-context'
import { FormField } from './FormField'

interface CertificateUploadFieldProps {
  fileName: string
  certPassword: string
  onChangeCertPassword: (value: string) => void
  onPickFile: () => void
  errorMessage?: string | null
}

/**
 * Selector de archivo p12 + clave, usado por el wizard de onboarding y por el
 * reemplazo de certificado en el detalle de tenant. Requiere `useCertificateFilePicker`
 * para `fileName`/`onPickFile`.
 */
export function CertificateUploadField({
  fileName,
  certPassword,
  onChangeCertPassword,
  onPickFile,
  errorMessage,
}: CertificateUploadFieldProps) {
  const { semantic } = useTheme()

  return (
    <>
      <Pressable
        onPress={onPickFile}
        style={[
          styles.fileBox,
          { borderColor: semantic.border.default, backgroundColor: semantic.bg.primary },
        ]}
      >
        <Ionicons name="cloud-upload-outline" size={28} color={semantic.accent.default} />
        <View style={styles.fileText}>
          <Text style={[styles.fileTitle, { color: semantic.text.primary }]}>
            {fileName || 'Seleccionar archivo p12'}
          </Text>
          <Text style={[styles.fileHint, { color: semantic.text.secondary }]}>
            Archivo p12 o pfx emitido para tu RUC
          </Text>
        </View>
      </Pressable>

      <FormField
        label="Clave del certificado"
        placeholder="Clave del p12"
        secureTextEntry
        leftIcon="key-outline"
        value={certPassword}
        onChangeText={onChangeCertPassword}
        required
      />

      {errorMessage ? (
        <Text style={[styles.errorText, { color: semantic.status.error }]}>{errorMessage}</Text>
      ) : null}
    </>
  )
}

const styles = StyleSheet.create({
  fileBox: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderStyle: 'dashed',
    borderWidth: 1.5,
    flexDirection: 'row',
    gap: spacing[3],
    minHeight: 92,
    padding: spacing[4],
  },
  fileText: { flex: 1, gap: spacing[1] },
  fileTitle: { fontSize: typography.size.base, fontWeight: typography.weight.semibold },
  fileHint: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
  errorText: { fontSize: typography.size.sm },
})
