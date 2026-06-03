"""missing_indexes

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-03

Índices faltantes para queries frecuentes por tenant en tablas críticas.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # signing_certificates — get_active_for_tenant() y list_for_tenant()
    op.create_index(
        "idx_signing_certificates_tenant_estado",
        "signing_certificates",
        ["tenant_id", "estado", "created_at"],
    )

    # establecimientos — list_by_tenant()
    op.create_index(
        "idx_establecimientos_tenant_estado",
        "establecimientos",
        ["tenant_id", "estado"],
    )

    # puntos_emision — list_by_establecimiento()
    op.create_index(
        "idx_puntos_emision_establecimiento_estado",
        "puntos_emision",
        ["establecimiento_id", "estado"],
    )

    # email_dispatches — queries por comprobante_id en worker
    op.create_index(
        "idx_email_dispatches_comprobante",
        "email_dispatches",
        ["comprobante_id"],
    )

    # api_keys — queries por tenant
    op.create_index(
        "idx_api_keys_tenant",
        "api_keys",
        ["tenant_id"],
    )

    # webhooks — queries por tenant
    op.create_index(
        "idx_webhooks_tenant",
        "webhooks",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_webhooks_tenant", "webhooks")
    op.drop_index("idx_api_keys_tenant", "api_keys")
    op.drop_index("idx_email_dispatches_comprobante", "email_dispatches")
    op.drop_index("idx_puntos_emision_establecimiento_estado", "puntos_emision")
    op.drop_index("idx_establecimientos_tenant_estado", "establecimientos")
    op.drop_index("idx_signing_certificates_tenant_estado", "signing_certificates")
