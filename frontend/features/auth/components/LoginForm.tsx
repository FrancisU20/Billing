import React from 'react'
import { StyleSheet, View } from 'react-native'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { FormField } from '@/components/ui/FormField'
import { Button } from '@/components/ui/Button'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { spacing } from '@/constants/tokens'
import { loginSchema, type LoginFormValues } from '../schemas'
import type { ApiError } from '@/lib/api/errors'

interface LoginFormProps {
  onSubmit: (values: LoginFormValues) => void
  isLoading: boolean
  apiError: ApiError | null
  dark?: boolean
}

export function LoginForm({ onSubmit, isLoading, apiError, dark }: LoginFormProps) {
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) })

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
            dark={dark}
            required
          />
        )}
      />

      <Controller
        control={control}
        name="password"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Contraseña"
            placeholder="Tu contraseña"
            secureTextEntry
            autoComplete="password"
            leftIcon="lock-closed-outline"
            error={errors.password?.message}
            onChangeText={onChange}
            onBlur={onBlur}
            value={value}
            dark={dark}
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
        Iniciar sesión
      </Button>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[4] },
})
