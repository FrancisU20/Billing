import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useTheme } from '@/lib/theme-context'
import { FormField } from '@/components/ui/FormField'
import { Button } from '@/components/ui/Button'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { typography, spacing, radius } from '@/constants/tokens'
import { newPasswordSchema, type NewPasswordFormValues } from '../schemas'
import type { ApiError } from '@/lib/api/errors'

interface ChallengeFormProps {
  onSubmit: (values: NewPasswordFormValues) => void
  isLoading: boolean
  apiError: ApiError | null
}

export function ChallengeForm({ onSubmit, isLoading, apiError }: ChallengeFormProps) {
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<NewPasswordFormValues>({
    resolver: zodResolver(newPasswordSchema),
  })
  const { semantic } = useTheme()

  return (
    <View style={staticStyles.container}>
      <View
        style={[
          staticStyles.hint,
          { backgroundColor: semantic.accent.subtle, borderLeftColor: semantic.accent.default },
        ]}
      >
        <Text style={[staticStyles.hintText, { color: semantic.text.primary }]}>
          Este es tu primer inicio de sesión. Debes establecer una nueva contraseña para continuar.
        </Text>
      </View>

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
        Establecer contraseña
      </Button>
    </View>
  )
}

const staticStyles = StyleSheet.create({
  container: { gap: spacing[4] },
  hint: { borderRadius: radius.md, padding: spacing[3], borderLeftWidth: 3 },
  hintText: { fontSize: typography.size.sm, lineHeight: typography.size.sm * 1.6 },
})
