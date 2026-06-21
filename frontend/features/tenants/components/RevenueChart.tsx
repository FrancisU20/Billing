import React, { useState } from 'react'
import { StyleSheet, View, type LayoutChangeEvent } from 'react-native'
import Svg, { Line, Path, Text as SvgText } from 'react-native-svg'
import { useTheme } from '@/lib/theme-context'
import { formatCurrency, formatDate } from '@/lib/utils/format'
import { typography } from '@/constants/tokens'
import type { DailyRevenuePoint } from '@/features/tenants/schemas'

interface RevenueChartProps {
  data: DailyRevenuePoint[]
}

const HEIGHT = 180
const LEFT_PADDING = 52
const TOP_PADDING = 10
const BOTTOM_PADDING = 24
const Y_AXIS_MARKS = 4
// react-native-web resuelve `fontFamily: 'System'` (typography.fontFamily.sans) a este
// stack para <Text> normal, pero <SvgText> escribe el valor literal al CSS del SVG en
// web — 'System' no es una font-family real ahi, asi que cae al serif default del
// navegador. Mismo stack que createReactDOMStyle.js de react-native-web para que el
// chart se vea igual que el resto de la app.
const SVG_TEXT_FONT_FAMILY =
  '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif'

export function RevenueChart({ data }: RevenueChartProps) {
  const { semantic } = useTheme()
  const [width, setWidth] = useState(0)

  const onLayout = (event: LayoutChangeEvent) => setWidth(event.nativeEvent.layout.width)

  if (width === 0) {
    return <View style={styles.container} onLayout={onLayout} />
  }

  const amounts = data.map((point) => Number(point.amount))
  const maxAmount = Math.max(...amounts, 1)
  const plotWidth = width - LEFT_PADDING
  const plotHeight = HEIGHT - TOP_PADDING - BOTTOM_PADDING

  const xAt = (index: number) =>
    LEFT_PADDING + (data.length > 1 ? (index / (data.length - 1)) * plotWidth : 0)
  const yAt = (amount: number) => TOP_PADDING + (1 - amount / maxAmount) * plotHeight

  const linePath = amounts
    .map((amount, index) => `${index === 0 ? 'M' : 'L'} ${xAt(index)},${yAt(amount)}`)
    .join(' ')
  const areaPath = `${linePath} L ${xAt(amounts.length - 1)},${TOP_PADDING + plotHeight} L ${xAt(0)},${TOP_PADDING + plotHeight} Z`

  const xLabelStep = Math.max(1, Math.ceil(data.length / 6))
  const xLabelIndexes = data
    .map((_, index) => index)
    .filter((index) => index % xLabelStep === 0 || index === data.length - 1)

  return (
    <View style={styles.container} onLayout={onLayout}>
      <Svg width={width} height={HEIGHT}>
        {Array.from({ length: Y_AXIS_MARKS }, (_, mark) => {
          const fraction = mark / (Y_AXIS_MARKS - 1)
          const amount = maxAmount * fraction
          const y = yAt(amount)
          return (
            <React.Fragment key={mark}>
              <Line
                x1={LEFT_PADDING}
                y1={y}
                x2={width}
                y2={y}
                stroke={semantic.chart.track}
                strokeWidth={1}
              />
              <SvgText
                x={LEFT_PADDING - 8}
                y={y + 4}
                fontSize={typography.size.xs}
                fontFamily={SVG_TEXT_FONT_FAMILY}
                fill={semantic.text.secondary}
                textAnchor="end"
              >
                {formatCurrency(amount)}
              </SvgText>
            </React.Fragment>
          )
        })}

        <Path d={areaPath} fill={semantic.accent.subtle} />
        <Path d={linePath} fill="none" stroke={semantic.chart.primary} strokeWidth={2} />

        {xLabelIndexes.map((index) => (
          <SvgText
            key={data[index].date}
            x={xAt(index)}
            y={HEIGHT - 6}
            fontSize={typography.size.xs}
            fontFamily={SVG_TEXT_FONT_FAMILY}
            fill={semantic.text.secondary}
            textAnchor="middle"
          >
            {formatDate(data[index].date)}
          </SvgText>
        ))}
      </Svg>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { height: HEIGHT, width: '100%' },
})
