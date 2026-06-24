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
  const sdkRootRef = useRef<HTMLElement | null>(null)
  const [sdkReady, setSdkReady] = useState(false)
  const [sdkError, setSdkError] = useState<string | null>(null)

  const unmountField = () => {
    if (fieldRef.current) {
      try {
        fieldRef.current.unmount()
      } catch {
        // SDK unmount errors are non-recoverable; suppress silently
      }
      fieldRef.current = null
    }
    sdkRootRef.current?.remove()
    sdkRootRef.current = null
  }

  const mountField = (wrapper: HTMLElement) => {
    wrapper.innerHTML = ''
    const fields = window.dlocalGo!.fields()
    const cardField = fields.create('card', getDLocalCardFieldOptions(semantic))
    const sdkRoot = document.createElement('div')
    sdkRoot.style.cssText = 'width:100%;height:100%'
    wrapper.appendChild(sdkRoot)
    cardField.mount(sdkRoot)
    fieldRef.current = cardField
    sdkRootRef.current = sdkRoot
  }

  useEffect(() => {
    setSdkReady(false)
    setSdkError(null)

    if (Platform.OS !== 'web' || !checkoutToken) return

    if (!config.dlocalgo.smartFieldsKey) {
      setSdkError('SmartFields key not configured.')
      return
    }

    let cancelled = false

    const init = async () => {
      if (cancelled) return
      try {
        await window.dlocalGo!.initialize(config.dlocalgo.smartFieldsKey, checkoutToken)
        if (cancelled) return
        const wrapper = document.getElementById(containerId)
        if (!wrapper) throw new Error(`Container #${containerId} not found`)
        mountField(wrapper)
        if (cancelled) {
          unmountField()
          return
        }
        setSdkReady(true)
      } catch (e) {
        if (!cancelled) {
          console.error('[dLocal SmartFields]', e)
          setSdkError('Error al inicializar el formulario de pago.')
        }
      }
    }

    // The SDK script registers a global zoid listener at load time and throws if
    // loaded twice on the same page, so it must be injected at most once per page
    // lifetime. `initialize()` itself is safe to call again with a new token on the
    // existing `window.dlocalGo` instance (that's how retrying with a new order works).
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
      unmountField()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checkoutToken, containerId])

  // The container is a plain View the caller may stop rendering (e.g. while showing
  // a 3DS verification step) and render again later without changing checkoutToken,
  // which destroys the mounted field's DOM node without re-running the effect above.
  // Re-attach the field whenever its container comes back. Deliberately runs after
  // every render (no deps array) to detect that reattachment.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!sdkReady || Platform.OS !== 'web') return
    if (sdkRootRef.current?.isConnected) return
    const wrapper = document.getElementById(containerId)
    if (!wrapper) return
    try {
      mountField(wrapper)
    } catch (e) {
      console.error('[dLocal SmartFields]', e)
      setSdkError('Error al inicializar el formulario de pago.')
    }
  })

  return { fieldRef, sdkReady, sdkError }
}
