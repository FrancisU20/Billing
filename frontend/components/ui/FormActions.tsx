import React from 'react'
import { StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native'
import { Button } from '@/components/ui/Button'
import { useTheme } from '@/lib/theme-context'
import { spacing, typography } from '@/constants/tokens'

interface FormActionsProps {
  submitLabel: string
  onSubmit: () => void
  isSubmitting?: boolean
  isSubmitDisabled?: boolean
  cancelLabel?: string
  onCancel?: () => void
  validationHint?: string
  style?: StyleProp<ViewStyle>
}

export function FormActions({
  submitLabel,
  onSubmit,
  isSubmitting = false,
  isSubmitDisabled = false,
  cancelLabel = 'Cancelar',
  onCancel,
  validationHint = 'Revisa los campos marcados antes de continuar.',
  style,
}: FormActionsProps) {
  const { semantic } = useTheme()
  const showValidationHint = isSubmitDisabled && !isSubmitting

  return (
    <View style={[styles.container, style]}>
      {showValidationHint ? (
        <Text style={[styles.hint, { color: semantic.text.secondary }]}>{validationHint}</Text>
      ) : null}
      <View style={styles.actions}>
        {onCancel ? (
          <Button
            variant="ghost"
            size="lg"
            fullWidth
            isDisabled={isSubmitting}
            onPress={onCancel}
            style={styles.button}
          >
            {cancelLabel}
          </Button>
        ) : null}
        <Button
          variant="primary"
          size="lg"
          fullWidth
          isLoading={isSubmitting}
          isDisabled={isSubmitDisabled}
          onPress={onSubmit}
          style={styles.button}
        >
          {submitLabel}
        </Button>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[2] },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  button: { flex: 1, minWidth: 180 },
  hint: { fontSize: typography.size.xs, lineHeight: typography.size.xs * 1.45 },
})
