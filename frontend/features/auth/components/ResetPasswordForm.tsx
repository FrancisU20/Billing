import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useTheme } from '@/lib/theme-context'
import { FormField } from '@/components/ui/FormField'
import { Button } from '@/components/ui/Button'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { typography, spacing, radius } from '@/constants/tokens'
import { resetPasswordSchema, type ResetPasswordFormValues } from '../schemas'
import type { ApiError } from '@/lib/api/errors'

interface ResetPasswordFormProps {
  email: string
  onSubmit: (values: ResetPasswordFormValues) => void
  isLoading: boolean
  apiError: ApiError | null
}

export function ResetPasswordForm({
  email,
  onSubmit,
  isLoading,
  apiError,
}: ResetPasswordFormProps) {
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({ resolver: zodResolver(resetPasswordSchema) })
  const { semantic } = useTheme()

  return (
    <View style={styles.container}>
      <View
        style={[
          styles.hint,
          { backgroundColor: semantic.accent.subtle, borderLeftColor: semantic.accent.default },
        ]}
      >
        <Text style={[styles.hintText, { color: semantic.text.primary }]}>
          Te enviamos un código de recuperación a {email}. Ingrésalo junto con tu nueva contraseña.
        </Text>
      </View>

      <Controller
        control={control}
        name="confirmationCode"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Código de recuperación"
            placeholder="123456"
            keyboardType="number-pad"
            leftIcon="keypad-outline"
            error={errors.confirmationCode?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
            required
          />
        )}
      />

      <Controller
        control={control}
        name="newPassword"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Nueva contraseña"
            placeholder="Mínimo 8 caracteres"
            secureTextEntry
            leftIcon="lock-open-outline"
            hint="Debe incluir mayúsculas y números"
            error={errors.newPassword?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
            required
          />
        )}
      />

      <Controller
        control={control}
        name="confirmPassword"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Confirmar contraseña"
            placeholder="Repite la contraseña"
            secureTextEntry
            leftIcon="shield-checkmark-outline"
            error={errors.confirmPassword?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
            required
          />
        )}
      />

      {apiError ? <ApiErrorBanner error={apiError} /> : null}

      <Button
        variant="primary"
        size="lg"
        fullWidth
        isLoading={isLoading}
        onPress={handleSubmit(onSubmit)}
      >
        Restablecer contraseña
      </Button>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[4] },
  hint: { borderRadius: radius.md, padding: spacing[3], borderLeftWidth: 3 },
  hintText: { fontSize: typography.size.sm, lineHeight: typography.size.sm * 1.6 },
})
