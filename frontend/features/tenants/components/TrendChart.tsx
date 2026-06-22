import React, { useState } from 'react'
import { StyleSheet, View, type LayoutChangeEvent } from 'react-native'
import Svg, { Line, Path, Text as SvgText } from 'react-native-svg'
import { useTheme } from '@/lib/theme-context'
import { formatCurrency, formatDate } from '@/lib/utils/format'
import { typography } from '@/constants/tokens'

export interface TrendChartPoint {
  date: string
  value: number
}

interface TrendChartProps {
  data: TrendChartPoint[]
  formatValue?: (value: number) => string
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

export function TrendChart({ data, formatValue = formatCurrency }: TrendChartProps) {
  const { semantic } = useTheme()
  const [width, setWidth] = useState(0)

  const onLayout = (event: LayoutChangeEvent) => setWidth(event.nativeEvent.layout.width)

  if (width === 0) {
    return <View style={styles.container} onLayout={onLayout} />
  }

  const values = data.map((point) => point.value)
  const maxValue = Math.max(...values, 1)
  const plotWidth = width - LEFT_PADDING
  const plotHeight = HEIGHT - TOP_PADDING - BOTTOM_PADDING

  const xAt = (index: number) =>
    LEFT_PADDING + (data.length > 1 ? (index / (data.length - 1)) * plotWidth : 0)
  const yAt = (value: number) => TOP_PADDING + (1 - value / maxValue) * plotHeight

  const linePath = values
    .map((value, index) => `${index === 0 ? 'M' : 'L'} ${xAt(index)},${yAt(value)}`)
    .join(' ')
  const areaPath = `${linePath} L ${xAt(values.length - 1)},${TOP_PADDING + plotHeight} L ${xAt(0)},${TOP_PADDING + plotHeight} Z`

  const xLabelStep = Math.max(1, Math.ceil(data.length / 6))
  const xLabelIndexes = data
    .map((_, index) => index)
    .filter((index) => index % xLabelStep === 0 || index === data.length - 1)

  return (
    <View style={styles.container} onLayout={onLayout}>
      <Svg width={width} height={HEIGHT}>
        {Array.from({ length: Y_AXIS_MARKS }, (_, mark) => {
          const fraction = mark / (Y_AXIS_MARKS - 1)
          const value = maxValue * fraction
          const y = yAt(value)
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
                {formatValue(value)}
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
