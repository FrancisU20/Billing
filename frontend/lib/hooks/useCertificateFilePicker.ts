import { useState } from 'react'
import { Platform } from 'react-native'

interface CertificateFilePickerInit {
  fileName?: string
  certificateB64?: string
}

/**
 * Selector de archivo `.p12`/`.pfx` para web — usado por el wizard de onboarding y
 * por la gestión post-onboarding del certificado. Solo funciona en `Platform.OS ===
 * 'web'`; en otras plataformas, `pickFile` deja un mensaje en `error`.
 */
export function useCertificateFilePicker(init: CertificateFilePickerInit = {}) {
  const [fileName, setFileName] = useState(init.fileName ?? '')
  const [certificateB64, setCertificateB64] = useState(init.certificateB64 ?? '')
  const [error, setError] = useState<string | null>(null)

  const pickFile = () => {
    setError(null)
    if (Platform.OS !== 'web' || typeof document === 'undefined') {
      setError('La carga de certificado está disponible en la versión web.')
      return
    }

    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.p12,.pfx,application/x-pkcs12'
    input.onchange = () => {
      const file = input.files?.[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = () => {
        const value = String(reader.result ?? '')
        const [, base64] = value.split(',')
        if (!base64) {
          setError('No se pudo leer el certificado seleccionado.')
          return
        }
        setFileName(file.name)
        setCertificateB64(base64)
      }
      reader.onerror = () => setError('No se pudo leer el certificado seleccionado.')
      reader.readAsDataURL(file)
    }
    input.click()
  }

  const reset = () => {
    setFileName('')
    setCertificateB64('')
    setError(null)
  }

  return { fileName, certificateB64, error, pickFile, reset }
}
