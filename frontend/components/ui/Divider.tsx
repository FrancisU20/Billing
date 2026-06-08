import React from 'react'
import { View } from 'react-native'
import { useTheme } from '@/lib/theme-context'

export function Divider({ vertical = false }: { vertical?: boolean }) {
  const { semantic } = useTheme()
  return (
    <View
      style={
        vertical
          ? { width: 1, backgroundColor: semantic.border.default, alignSelf: 'stretch' }
          : { height: 1, backgroundColor: semantic.border.default, width: '100%' }
      }
    />
  )
}
