import { useEffect, useRef, useState } from 'react'
import { Platform } from 'react-native'
import { config } from '@/constants/config'
import type { SemanticTokens } from '@/constants/tokens'
import type { DLocalGoField } from './dlocal-types'
import { getDLocalCardFieldOptions } from './dlocal-field-options'

interface Options {
  checkoutToken: string | undefined
  containerId: string
  semantic: SemanticTokens
}

export interface UseDLocalSmartFieldsResult {
  fieldRef: React.MutableRefObject<DLocalGoField | null>
  sdkReady: boolean
  sdkError: string | null
}

export function useDLocalSmartFields({
  checkoutToken,
  containerId,
  semantic,
}: Options): UseDLocalSmartFieldsResult {
  const fieldRef = useRef<DLocalGoField | null>(null)
  const initializedRef = useRef(false)
  const [sdkReady, setSdkReady] = useState(false)
  const [sdkError, setSdkError] = useState<string | null>(null)

  useEffect(() => {
    setSdkReady(false)
    setSdkError(null)

    if (Platform.OS !== 'web' || !checkoutToken) return

    if (!config.dlocalgo.smartFieldsKey) {
      setSdkError('SmartFields key not configured.')
      return
    }

    initializedRef.current = false
    let cancelled = false

    const init = async () => {
      if (initializedRef.current || cancelled) return
      initializedRef.current = true
      try {
        await window.dlocalGo!.initialize(config.dlocalgo.smartFieldsKey, checkoutToken)
        if (cancelled) return
        const fields = window.dlocalGo!.fields()
        const cardField = fields.create('card', getDLocalCardFieldOptions(semantic))
        const wrapper = document.getElementById(containerId)
        if (!wrapper) throw new Error(`Container #${containerId} not found`)
        const sdkRoot = document.createElement('div')
        sdkRoot.style.cssText = 'width:100%;height:100%'
        wrapper.appendChild(sdkRoot)
        cardField.mount(sdkRoot)
        if (cancelled) {
          cardField.unmount()
          return
        }
        fieldRef.current = cardField
        setSdkReady(true)
      } catch (e) {
        if (!cancelled) {
          console.error('[dLocal SmartFields]', e)
          initializedRef.current = false
          setSdkError('Error al inicializar el formulario de pago.')
        }
      }
    }

    const scriptId = 'dlocalgo-smartfields-sdk'
    if (document.getElementById(scriptId)) {
      if (window.dlocalGo) init()
    } else {
      const script = document.createElement('script')
      script.id = scriptId
      script.src = config.dlocalgo.sdkUrl
      script.onload = init
      script.onerror = () => {
        if (!cancelled) setSdkError('No se pudo cargar el formulario de pago.')
      }
      document.head.appendChild(script)
    }

    return () => {
      cancelled = true
      if (fieldRef.current) {
        try {
          fieldRef.current.unmount()
        } catch {
          // SDK unmount errors are non-recoverable; suppress silently
        }
        fieldRef.current = null
      }
      initializedRef.current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checkoutToken, containerId])

  return { fieldRef, sdkReady, sdkError }
}
