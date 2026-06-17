import type { SemanticTokens } from '@/constants/tokens'
import { typography } from '@/constants/tokens'
import type { DLocalCardFieldOptions } from './dlocal-types'

// 'System' es nombre React Native — el iframe del SDK necesita una font stack CSS válida.
const WEB_FONT_FAMILY = 'system-ui, -apple-system, BlinkMacSystemFont, sans-serif'

export function getDLocalCardFieldOptions(semantic: SemanticTokens): DLocalCardFieldOptions {
  return {
    style: {
      base: {
        color: semantic.text.primary,
        fontSize: `${typography.size.md}px`,
        fontFamily: WEB_FONT_FAMILY,
        fontWeight: typography.weight.regular,
        lineHeight: '48px',
      },
      // SDK ignores ::placeholder in base; `empty` state controls placeholder color.
      empty: {
        color: semantic.text.secondary,
        fontWeight: typography.weight.regular,
      },
      invalid: {
        color: semantic.status.error,
      },
    },
  }
}
