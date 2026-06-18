import React from 'react'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { IVA_RATE_OPTIONS } from '../constants'
import type { IvaRate } from '../types'

interface IvaRatePickerProps {
  value: IvaRate
  onChange: (value: IvaRate) => void
}

export function IvaRatePicker({ value, onChange }: IvaRatePickerProps) {
  return <SegmentedControl<IvaRate> options={IVA_RATE_OPTIONS} value={value} onChange={onChange} />
}
