function randomByte(): number {
  return Math.floor(Math.random() * 256)
}

function getRandomBytes(): Uint8Array {
  const bytes = new Uint8Array(16)
  const cryptoSource = globalThis.crypto
  if (cryptoSource?.getRandomValues) {
    cryptoSource.getRandomValues(bytes)
    return bytes
  }
  for (let index = 0; index < bytes.length; index += 1) {
    bytes[index] = randomByte()
  }
  return bytes
}

export function generateProductSku(): string {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID().toUpperCase()
  }

  const bytes = getRandomBytes()
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80

  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0'))
  return [
    hex.slice(0, 4).join(''),
    hex.slice(4, 6).join(''),
    hex.slice(6, 8).join(''),
    hex.slice(8, 10).join(''),
    hex.slice(10, 16).join(''),
  ]
    .join('-')
    .toUpperCase()
}

export const SKU_PLACEHOLDER = 'UUID del producto'
