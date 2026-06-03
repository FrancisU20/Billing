"""fk_cascade

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-03

Agrega ON DELETE CASCADE a FKs que deben seguir el ciclo de vida de su padre:
- signing_certificates.tenant_id → tenants.id
- email_dispatches.comprobante_id → comprobantes.id

PostgreSQL requiere DROP + recrear el constraint para cambiar su comportamiento.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # signing_certificates → tenants
    op.drop_constraint("signing_certificates_tenant_id_fkey", "signing_certificates", type_="foreignkey")
    op.create_foreign_key(
        "signing_certificates_tenant_id_fkey",
        "signing_certificates", "tenants",
        ["tenant_id"], ["id"],
        ondelete="CASCADE",
    )

    # email_dispatches → comprobantes
    op.drop_constraint("email_dispatches_comprobante_id_fkey", "email_dispatches", type_="foreignkey")
    op.create_foreign_key(
        "email_dispatches_comprobante_id_fkey",
        "email_dispatches", "comprobantes",
        ["comprobante_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("email_dispatches_comprobante_id_fkey", "email_dispatches", type_="foreignkey")
    op.create_foreign_key(
        "email_dispatches_comprobante_id_fkey",
        "email_dispatches", "comprobantes",
        ["comprobante_id"], ["id"],
    )

    op.drop_constraint("signing_certificates_tenant_id_fkey", "signing_certificates", type_="foreignkey")
    op.create_foreign_key(
        "signing_certificates_tenant_id_fkey",
        "signing_certificates", "tenants",
        ["tenant_id"], ["id"],
    )
