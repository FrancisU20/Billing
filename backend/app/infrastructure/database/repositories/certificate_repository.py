from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models.signing_certificate import SigningCertificateModel


class CertificateRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        tenant_id: UUID,
        nombre: str | None,
        s3_key: str,
        secrets_manager_arn: str,
        fecha_emision,
        fecha_expiracion,
    ) -> SigningCertificateModel:
        model = SigningCertificateModel(
            tenant_id=tenant_id,
            nombre=nombre,
            s3_key=s3_key,
            secrets_manager_arn=secrets_manager_arn,
            fecha_emision=fecha_emision,
            fecha_expiracion=fecha_expiracion,
            estado="ACTIVE",
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_active_for_tenant(self, tenant_id: UUID) -> SigningCertificateModel | None:
        result = await self._session.execute(
            select(SigningCertificateModel)
            .where(
                SigningCertificateModel.tenant_id == tenant_id,
                SigningCertificateModel.estado == "ACTIVE",
            )
            .order_by(SigningCertificateModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_tenant(self, tenant_id: UUID) -> list[SigningCertificateModel]:
        result = await self._session.execute(
            select(SigningCertificateModel)
            .where(SigningCertificateModel.tenant_id == tenant_id)
            .order_by(SigningCertificateModel.created_at.desc())
        )
        return list(result.scalars().all())
