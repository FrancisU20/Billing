import React, { useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { FormField } from '@/components/ui/FormField'
import { EmailField, IdentificationField } from '@/components/ui/SpecializedFields'
import { radius, spacing, typography } from '@/constants/tokens'
import { isEmailInput } from '@/lib/utils/form-validators'
import { isValidCedula, isValidRuc } from '@/lib/utils/ruc'
import { useTheme } from '@/lib/theme-context'

export interface PayerFormValues {
  firstName: string
  lastName: string
  payerEmail: string
  documentType: 'CI' | 'RUC'
  payerDocument: string
}

interface PayerFormSetters {
  setFirstName: (v: string) => void
  setLastName: (v: string) => void
  setPayerEmail: (v: string) => void
  setDocumentType: (v: 'CI' | 'RUC') => void
  setPayerDocument: (v: string) => void
}

export interface UsePayerFormReturn {
  values: PayerFormValues
  setters: PayerFormSetters
  isComplete: boolean
  reset: () => void
}

export function usePayerForm(): UsePayerFormReturn {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [payerEmail, setPayerEmail] = useState('')
  const [documentType, setDocumentType] = useState<'CI' | 'RUC'>('CI')
  const [payerDocument, setPayerDocument] = useState('')

  const isComplete =
    !!firstName.trim() &&
    !!lastName.trim() &&
    isEmailInput(payerEmail) &&
    (documentType === 'CI' ? isValidCedula(payerDocument) : isValidRuc(payerDocument))

  function reset() {
    setFirstName('')
    setLastName('')
    setPayerEmail('')
    setDocumentType('CI')
    setPayerDocument('')
  }

  return {
    values: { firstName, lastName, payerEmail, documentType, payerDocument },
    setters: { setFirstName, setLastName, setPayerEmail, setDocumentType, setPayerDocument },
    isComplete,
    reset,
  }
}

interface PayerFormProps {
  values: PayerFormValues
  setters: PayerFormSetters
}

export function PayerForm({ values, setters }: PayerFormProps) {
  const { semantic } = useTheme()
  const { firstName, lastName, payerEmail, documentType, payerDocument } = values
  const { setFirstName, setLastName, setPayerEmail, setDocumentType, setPayerDocument } = setters
  const emailError = payerEmail && !isEmailInput(payerEmail) ? 'Email inválido' : undefined
  const documentError =
    payerDocument &&
    !(documentType === 'CI' ? isValidCedula(payerDocument) : isValidRuc(payerDocument))
      ? documentType === 'CI'
        ? 'Cédula ecuatoriana inválida'
        : 'RUC ecuatoriano inválido'
      : undefined

  return (
    <>
      <Text style={[styles.sectionLabel, { color: semantic.text.primary }]}>Datos del pagador</Text>

      <View style={styles.nameRow}>
        <View style={styles.nameField}>
          <FormField
            label="Nombre"
            value={firstName}
            onChangeText={setFirstName}
            placeholder="Nombre"
            autoCapitalize="words"
            autoCorrect={false}
          />
        </View>
        <View style={styles.nameField}>
          <FormField
            label="Apellido"
            value={lastName}
            onChangeText={setLastName}
            placeholder="Apellido"
            autoCapitalize="words"
            autoCorrect={false}
          />
        </View>
      </View>

      <EmailField
        label="Email"
        value={payerEmail}
        onChangeText={setPayerEmail}
        placeholder="correo@ejemplo.com"
        autoCorrect={false}
        error={emailError}
      />

      <View style={styles.docGroup}>
        <Text style={[styles.docLabel, { color: semantic.text.primary }]}>Tipo de documento</Text>
        <View style={styles.docTypeRow}>
          {(['CI', 'RUC'] as const).map((type) => (
            <Pressable
              key={type}
              onPress={() => setDocumentType(type)}
              style={[
                styles.docTypeBtn,
                {
                  borderColor:
                    documentType === type ? semantic.accent.default : semantic.border.default,
                  backgroundColor: documentType === type ? semantic.accent.subtle : 'transparent',
                },
              ]}
            >
              <Text
                style={[
                  styles.docTypeBtnText,
                  {
                    color:
                      documentType === type ? semantic.accent.default : semantic.text.secondary,
                  },
                ]}
              >
                {type === 'CI' ? 'Cédula' : 'RUC'}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      <IdentificationField
        identificationType={documentType === 'CI' ? 'cedula' : 'ruc'}
        label="Número de documento"
        value={payerDocument}
        onChangeText={setPayerDocument}
        placeholder={documentType === 'CI' ? '10 dígitos' : '13 dígitos'}
        autoCorrect={false}
        error={documentError}
      />
    </>
  )
}

const styles = StyleSheet.create({
  sectionLabel: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
    marginTop: spacing[1],
  },
  nameRow: { flexDirection: 'row', gap: spacing[3] },
  nameField: { flex: 1 },
  docGroup: { gap: spacing[1] + 2 },
  docLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  docTypeRow: { flexDirection: 'row', gap: spacing[2] },
  docTypeBtn: {
    flex: 1,
    height: 48,
    borderWidth: 1,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  docTypeBtnText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
})
