from __future__ import annotations

"""0005_backfill_product_invoice_code — Product.invoice_code para productos viejos.

`invoice_code` es el codigoPrincipal/codigoAuxiliar que viaja en el XML de
factura (limite SRI: 25 caracteres, ver Ficha Tecnica SRI Anexo 1). Antes de
este cambio se usaba `sku` directamente para esto, lo que forzaba el formato
del SRI sobre el codigo propio del tenant. Productos creados antes de este
cambio no tienen `invoice_code`: se backfillea derivandolo del `sku` existente
con la misma regla que usa el dominio (`Product._derive_invoice_code`) — si el
sku ya entra en el limite se reusa tal cual, si no se genera un codigo corto
aleatorio. El `sku` del producto nunca se modifica.
"""

from lambdas.products.domain.entity import _derive_invoice_code
from migrations.context import MigrationContext, MigrationResult

MIGRATION_ID = "0005_backfill_product_invoice_code"
DESCRIPTION = "Backfill Product.invoice_code derivado del sku existente."


def run(context: MigrationContext) -> MigrationResult:
    products_table = context.table("PRODUCTS_TABLE")

    updated = 0
    skipped = 0
    details: list[str] = []

    scan_kwargs: dict = {}
    while True:
        response = products_table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            if item.get("entity_type") != "PRODUCT":
                continue

            product_id = item["id"]
            if item.get("invoice_code"):
                skipped += 1
                details.append(f"skipped:product:{product_id}:already_set")
                continue

            invoice_code = _derive_invoice_code(item["sku"], current=None)
            products_table.update_item(
                Key={"pk": item["pk"], "sk": item["sk"]},
                UpdateExpression="SET invoice_code = :invoice_code",
                ExpressionAttributeValues={":invoice_code": invoice_code},
            )
            updated += 1
            details.append(f"updated:product:{product_id}:{invoice_code}")

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return MigrationResult(updated=updated, skipped=skipped, details=details)
