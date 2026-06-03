"""rls_policies

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-03

Crea las políticas RLS prometidas en migración 0001.

Estrategia:
- clbilling_admin es el rol de servicio. Se le da bypass explícito para que
  el esquema sea auto-documentado (superusers ya bypass RLS por defecto).
- Tablas con tenant_id reciben política de aislamiento basada en la variable
  de sesión app.tenant_id que el app establecerá en el futuro para aislamiento
  DB-level. Mientras tanto clbilling_admin es la única ruta de acceso.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tablas con columna tenant_id propia — política de aislamiento por tenant_id directo
TENANT_TABLES = [
    "comprobantes",
    "lotes",
    "signing_certificates",
    "establecimientos",
    "api_keys",
    "webhooks",
    "tenant_users",
]

# Tablas sin tenant_id directo — acceso solo al rol de servicio.
# El aislamiento multitenant se resuelve a nivel app o mediante JOIN con tablas que sí tienen tenant_id.
# email_dispatches: accede via comprobante_id → comprobantes.tenant_id (ya protegida por RLS)
# audit_log: tabla de auditoría interna
SERVICE_ONLY_TABLES = [
    "email_dispatches",
    "audit_log",
]


def upgrade() -> None:
    # Política de bypass para el rol de servicio en todas las tablas con RLS
    for table in TENANT_TABLES + SERVICE_ONLY_TABLES:
        op.execute(
            f"CREATE POLICY service_role_bypass ON {table} "
            f"TO clbilling_admin USING (true) WITH CHECK (true)"
        )

    # Política de aislamiento por tenant (preparada para uso futuro con SET LOCAL)
    # Cuando el app establezca: SET LOCAL app.tenant_id = '<uuid>'
    # esta política filtrará automáticamente los rows por tenant.
    for table in TENANT_TABLES:
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = current_setting('app.tenant_id', true)::uuid)"
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"DROP POLICY IF EXISTS service_role_bypass ON {table}")
    for table in SERVICE_ONLY_TABLES:
        op.execute(f"DROP POLICY IF EXISTS service_role_bypass ON {table}")
