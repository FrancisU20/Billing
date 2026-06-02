"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Planes ────────────────────────────────────────────────
    op.create_table(
        "planes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("nombre", sa.String(50), nullable=False),
        sa.Column("max_comprobantes_mes", sa.Integer, nullable=False),
        sa.Column("precio_usd", sa.Numeric(10, 2), nullable=True),
        sa.Column("features", JSONB, nullable=False, server_default="{}"),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── Tenants ───────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ruc", sa.String(13), nullable=False, unique=True),
        sa.Column("razon_social", sa.String(300), nullable=False),
        sa.Column("nombre_comercial", sa.String(300), nullable=True),
        sa.Column("estado", sa.String(30), nullable=False, server_default="TRIAL"),
        sa.Column("ambiente_sri", sa.String(10), nullable=False, server_default="PRUEBAS"),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("planes.id"), nullable=True),
        sa.Column("comprobantes_mes_actual", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "tenant_settings",
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("logo_s3_key", sa.String(500), nullable=True),
        sa.Column("color_primario", sa.String(7), nullable=True),
        sa.Column("color_secundario", sa.String(7), nullable=True),
        sa.Column("email_remitente", sa.String(255), nullable=True),
        sa.Column("nombre_remitente", sa.String(255), nullable=True),
        sa.Column("config_email", JSONB, nullable=False, server_default="{}"),
        sa.Column("campos_custom", JSONB, nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── Usuarios ──────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cognito_sub", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=True),
        sa.Column("es_superadmin", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("estado", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "tenant_users",
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("rol", sa.String(50), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── Firma electrónica ─────────────────────────────────────
    op.create_table(
        "signing_certificates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=True),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("secrets_manager_arn", sa.String(500), nullable=True),
        sa.Column("fecha_emision", sa.Date, nullable=True),
        sa.Column("fecha_expiracion", sa.Date, nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── Establecimientos y secuenciales ───────────────────────
    op.create_table(
        "establecimientos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("codigo", sa.String(3), nullable=False),
        sa.Column("direccion", sa.String(300), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.UniqueConstraint("tenant_id", "codigo", name="uq_establecimiento"),
    )

    op.create_table(
        "puntos_emision",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("establecimiento_id", UUID(as_uuid=True), sa.ForeignKey("establecimientos.id"), nullable=False),
        sa.Column("codigo", sa.String(3), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.UniqueConstraint("establecimiento_id", "codigo", name="uq_punto_emision"),
    )

    op.create_table(
        "secuenciales",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("punto_emision_id", UUID(as_uuid=True), sa.ForeignKey("puntos_emision.id"), nullable=False),
        sa.Column("tipo_comprobante", sa.String(10), nullable=False),
        sa.Column("secuencial_actual", sa.BigInteger, nullable=False, server_default="0"),
        sa.UniqueConstraint("punto_emision_id", "tipo_comprobante", name="uq_secuencial"),
    )

    # ── Comprobantes ──────────────────────────────────────────
    op.create_table(
        "comprobantes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("clave_acceso", sa.String(49), nullable=True, unique=True),
        sa.Column("establecimiento", sa.String(3), nullable=False),
        sa.Column("punto_emision", sa.String(3), nullable=False),
        sa.Column("secuencial", sa.String(9), nullable=True),
        sa.Column("estado", sa.String(40), nullable=False, server_default="DRAFT"),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("datos", JSONB, nullable=False),
        sa.Column("numero_autorizacion", sa.String(49), nullable=True),
        sa.Column("fecha_autorizacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("s3_key_xml", sa.String(500), nullable=True),
        sa.Column("s3_key_xml_firmado", sa.String(500), nullable=True),
        sa.Column("s3_key_xml_autorizado", sa.String(500), nullable=True),
        sa.Column("s3_key_pdf", sa.String(500), nullable=True),
        sa.Column("lote_id", UUID(as_uuid=True), nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_detalle", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "tipo", "establecimiento", "punto_emision", "secuencial", name="uq_comprobante_serie"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_comprobante_idempotency"),
    )
    op.create_index("idx_comprobantes_tenant_estado", "comprobantes", ["tenant_id", "estado"])
    op.create_index("idx_comprobantes_clave_acceso", "comprobantes", ["clave_acceso"])

    op.create_table(
        "comprobante_status_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("comprobante_id", UUID(as_uuid=True), sa.ForeignKey("comprobantes.id"), nullable=False),
        sa.Column("estado_anterior", sa.String(40), nullable=True),
        sa.Column("estado_nuevo", sa.String(40), nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "sri_submissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("comprobante_id", UUID(as_uuid=True), sa.ForeignKey("comprobantes.id"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("ambiente", sa.String(10), nullable=False),
        sa.Column("request_claveacceso", sa.String(49), nullable=True),
        sa.Column("response_estado", sa.String(30), nullable=True),
        sa.Column("response_mensajes", JSONB, nullable=True),
        sa.Column("duracion_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── Lotes ─────────────────────────────────────────────────
    op.create_table(
        "lotes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=True),
        sa.Column("estado", sa.String(30), nullable=False, server_default="UPLOADED"),
        sa.Column("s3_key_original", sa.String(500), nullable=True),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("validos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("invalidos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("procesados", sa.Integer, nullable=False, server_default="0"),
        sa.Column("autorizados", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fallidos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("errores_resumen", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── Correos ───────────────────────────────────────────────
    op.create_table(
        "email_dispatches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("comprobante_id", UUID(as_uuid=True), sa.ForeignKey("comprobantes.id"), nullable=False),
        sa.Column("proveedor", sa.String(30), nullable=True),
        sa.Column("destinatario", sa.String(255), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("intentos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_detalle", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("enviado_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── API Keys y Webhooks ───────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("key_prefix", sa.String(10), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("scopes", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("rate_limit_per_min", sa.Integer, nullable=False, server_default="60"),
        sa.Column("estado", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("ultimo_uso_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "webhooks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("eventos", ARRAY(sa.String), nullable=False),
        sa.Column("secret_hash", sa.String(255), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── Auditoría ─────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("operacion", sa.String(100), nullable=False),
        sa.Column("entidad", sa.String(50), nullable=True),
        sa.Column("entidad_id", UUID(as_uuid=True), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.Column("datos_antes", JSONB, nullable=True),
        sa.Column("datos_despues", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_audit_tenant_operacion", "audit_log", ["tenant_id", "operacion", "created_at"])

    # ── RLS: habilitar Row Level Security en tablas críticas ──
    # Las políticas se crean en la migración 0002 (requieren que el rol exista)
    for table in ["comprobantes", "lotes", "signing_certificates", "audit_log",
                  "establecimientos", "email_dispatches", "api_keys", "webhooks", "tenant_users"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # Bypass RLS para el rol de servicio (Lambda usa clbilling_admin que es superuser)
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    tables = [
        "audit_log", "webhooks", "api_keys", "email_dispatches", "lotes",
        "sri_submissions", "comprobante_status_history", "comprobantes",
        "secuenciales", "puntos_emision", "establecimientos",
        "signing_certificates", "tenant_users", "users",
        "tenant_settings", "tenants", "planes",
    ]
    for table in tables:
        op.drop_table(table)
