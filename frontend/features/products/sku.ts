function randomByte(): number {
  return Math.floor(Math.random() * 256)
}

function getRandomBytes(length: number): Uint8Array {
  const bytes = new Uint8Array(length)
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

// 10 random bytes -> 20 hex chars: well under the SRI codigoPrincipal/codigoAuxiliar
// limit of 25 chars (the document line code is filled straight from a product's
// sku), with enough entropy that collisions within a tenant's catalog are not a
// practical concern.
export function generateProductSku(): string {
  const bytes = getRandomBytes(10)
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0'))
    .join('')
    .toUpperCase()
}

export const SKU_PLACEHOLDER = 'Código del producto'
