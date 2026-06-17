export interface DLocalCardFieldOptions {
  style?: {
    base?: Record<string, string>
    empty?: Record<string, string>
    invalid?: Record<string, string>
    valid?: Record<string, string>
  }
}

export interface DLocalGoField {
  mount: (container: HTMLElement | string) => void
  unmount: () => void
}

interface DLocalGoFields {
  create: (type: string, options?: DLocalCardFieldOptions) => DLocalGoField
}

export interface DLocalGoInstance {
  initialize: (key: string, checkoutToken: string) => Promise<void>
  fields: () => DLocalGoFields
  createCardToken: (field: DLocalGoField, opts?: { name?: string }) => Promise<{ token: string }>
}

declare global {
  interface Window {
    dlocalGo?: DLocalGoInstance
  }
}
