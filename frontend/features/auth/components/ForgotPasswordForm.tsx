import React from 'react'
import { StyleSheet, View } from 'react-native'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { FormField } from '@/components/ui/FormField'
import { Button } from '@/components/ui/Button'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { spacing } from '@/constants/tokens'
import { forgotPasswordSchema, type ForgotPasswordFormValues } from '../schemas'
import type { ApiError } from '@/lib/api/errors'

interface ForgotPasswordFormProps {
  onSubmit: (values: ForgotPasswordFormValues) => void
  isLoading: boolean
  apiError: ApiError | null
}

export function ForgotPasswordForm({ onSubmit, isLoading, apiError }: ForgotPasswordFormProps) {
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormValues>({ resolver: zodResolver(forgotPasswordSchema) })

  return (
    <View style={styles.container}>
      <Controller
        control={control}
        name="username"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Email"
            placeholder="usuario@empresa.com"
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
            leftIcon="mail-outline"
            error={errors.username?.message}
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
        Enviar código de recuperación
      </Button>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[4] },
})
