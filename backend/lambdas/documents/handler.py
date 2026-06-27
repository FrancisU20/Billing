from __future__ import annotations

"""
Documents Lambda — electronic invoice emission and retrieval.

Routes:
    POST /documents                → emit_document (doc_type 01) o emit_credit_note
                                      (doc_type 04) — mismo endpoint, discriminado por
                                      doc_type en el body (202 Accepted)
    GET  /documents                → list_documents (?doc_type= opcional)
    GET  /documents/summary        → get_documents_summary
    GET  /documents/{id}           → get_document
    GET  /documents/{id}/ride      → get_ride_url (pre-signed S3 URL)
    GET  /documents/{id}/xml       → get_xml_url (pre-signed S3 URL)
    POST /documents/{id}/annul     → annul_document (legacy: marca local sin SRI,
                                      deprecado — la UI actual usa Nota de Credito)
    POST /documents/{id}/retry     → retry_document (solo status REJECTED — reusa la
                                      misma clave de acceso/secuencial, vuelve a SIGN)

Auth:
    - POST: owner, admin, superadmin
    - GET:  owner, admin, viewer, superadmin
    tenant_id always comes from JWT; superadmin may override via ?tenant_id=.
"""

import json
import re

import boto3

from lambdas._base.handler import lambda_handler
from lambdas._base.idempotency import idempotent, require_current_context
from lambdas._base.parser import Request, parse, require_path_param
from lambdas._base.permissions import require_role
from lambdas._base.response import ApiResponse
from lambdas.documents.domain.commands import (
    AnnulDocumentCommand,
    CreditNoteLineData,
    EmitCreditNoteCommand,
    EmitDocumentCommand,
    GetDocumentCommand,
    GetRideUrlCommand,
    GetXmlUrlCommand,
    LineData,
    ListDocumentsCommand,
    RetryDocumentCommand,
)
from lambdas.documents.domain.entities import DocumentStatus
from lambdas.documents.domain.errors import DocumentNotFoundError
from lambdas.documents.infra.discount_campaign_catalog import DynamoDiscountCampaignCatalog
from lambdas.documents.infra.documents_repository import DynamoDocumentsRepository
from lambdas.documents.infra.plan_reader import DynamoPlanReader
from lambdas.documents.infra.product_catalog import DynamoProductCatalog
from lambdas.documents.infra.sequences_adapter import DynamoSequencesAdapter
from lambdas.documents.schemas import (
    AnnulDocumentRequest,
    EmitCreditNoteRequest,
    EmitDocumentRequest,
    ListDocumentsQueryParams,
)
from lambdas.documents.use_cases.annul_document import AnnulDocumentUseCase
from lambdas.documents.use_cases.emit_credit_note import EmitCreditNoteUseCase
from lambdas.documents.use_cases.emit_document import EmitDocumentUseCase
from lambdas.documents.use_cases.get_document import GetDocumentUseCase
from lambdas.documents.use_cases.get_documents_summary import GetDocumentsSummaryUseCase
from lambdas.documents.use_cases.get_ride_url import GetRideUrlUseCase
from lambdas.documents.use_cases.get_xml_url import GetXmlUrlUseCase
from lambdas.documents.use_cases.list_documents import ListDocumentsUseCase
from lambdas.documents.use_cases.retry_document import RetryDocumentUseCase
from lambdas.tenants.domain.enums import SriEnvironment
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from shared.config import env
from shared.db.client import get_table
from shared.errors import ForbiddenError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)

_documents_table = get_table("DOCUMENTS_TABLE")
_sequences_table = get_table("SEQUENCES_TABLE")
_tenants_table = get_table("TENANTS_TABLE")
_plans_table = get_table("PLANS_TABLE")
_products_table = get_table("PRODUCTS_TABLE") if env("PRODUCTS_TABLE", "") else None
_audit_table = get_table("AUDIT_LOG_TABLE") if env("AUDIT_LOG_TABLE", "") else None
_sign_queue_url = env("SIGN_QUEUE_URL", "")
_documents_bucket = env("DOCUMENTS_BUCKET", "")


def _repo() -> DynamoDocumentsRepository:
    return DynamoDocumentsRepository(_documents_table, _audit_table)


def _sequences_port() -> DynamoSequencesAdapter:
    return DynamoSequencesAdapter(_sequences_table)


def _get_tenant(tenant_id: str):
    return DynamoTenantRepository(_tenants_table, None, None).get_by_id(tenant_id)


def _get_plan(plan_id: str):
    return DynamoPlanReader(_plans_table).get(plan_id)


def _product_catalog(tenant_id: str):
    if _products_table is None:
        return None
    return DynamoProductCatalog(tenant_id, _products_table)


def _discount_campaign_port(tenant_id: str):
    if _products_table is None:
        return None
    return DynamoDiscountCampaignCatalog(tenant_id, _products_table)


def _resolve_tenant_id(request: Request) -> str:
    if request.is_superadmin:
        return request.query_params.get("tenant_id") or request.tenant_id
    return request.tenant_id


def _send_sign_message(document_id: str, tenant_id: str) -> None:
    boto3.client("sqs").send_message(
        QueueUrl=_sign_queue_url,
        MessageBody=json.dumps(
            {"type": "SIGN", "document_id": document_id, "tenant_id": tenant_id}
        ),
    )


# ── Handlers ──────────────────────────────────────────────────────────────────


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _emit(request: Request, context) -> dict:
    """POST /documents — un solo endpoint para ambos tipos de comprobante, discriminado
    por doc_type en el body. La cola SIGN/POLL es agnostica al tipo (ver xml_builder/
    ride_builder), asi que el unico fork esta aqui, antes de construir el Document.
    """
    tenant_id = _resolve_tenant_id(request)
    if not request.is_superadmin and tenant_id != request.tenant_id:
        raise ForbiddenError()

    if request.body.get("doc_type") == "04":
        return _emit_credit_note(request, tenant_id)
    return _emit_invoice(request, tenant_id)


def _emit_invoice(request: Request, tenant_id: str) -> dict:
    body = parse(EmitDocumentRequest, request.body)

    tenant = _get_tenant(tenant_id)
    plan_info = _get_plan(tenant.plan_id)

    monthly_limit = (
        plan_info.pruebas_monthly_docs_limit
        if tenant.sri_environment == SriEnvironment.TESTING
        else plan_info.document_limit
    )

    serie = body.establishment_code + body.emission_point_code

    lines = [
        LineData(
            code=ln.code,
            description=ln.description,
            quantity=ln.quantity,
            unit_price=ln.unit_price,
            discount=ln.discount,
            iva_rate=ln.iva_rate,
            product_id=ln.product_id,
        )
        for ln in body.lines
    ]

    repo = _repo()
    seq_port = _sequences_port()

    document = EmitDocumentUseCase(
        repo,
        seq_port,
        _product_catalog(tenant_id),
        _discount_campaign_port(tenant_id),
    ).execute(
        EmitDocumentCommand(
            tenant_id=tenant_id,
            ruc=tenant.ruc,
            sri_environment=tenant.sri_environment.value,
            certificate_secret_arn=tenant.certificate_secret_arn,
            monthly_limit=monthly_limit,
            doc_type=body.doc_type,
            serie=serie,
            issued_at=body.issued_at,
            client_id=body.client_id,
            buyer_id_type=body.buyer_id_type,
            buyer_id=body.buyer_id,
            buyer_name=body.buyer_name,
            buyer_email=body.buyer_email,
            payment_method=body.payment_method,
            lines=lines,
            created_by=request.user_id,
            override_discount_ceiling=body.override_discount_ceiling,
            override_reason=body.override_reason,
        )
    )

    return _finalize_emission(
        document,
        request,
        repo,
        override_reason=body.override_reason if body.override_discount_ceiling else None,
    )


def _emit_credit_note(request: Request, tenant_id: str) -> dict:
    body = parse(EmitCreditNoteRequest, request.body)

    tenant = _get_tenant(tenant_id)
    plan_info = _get_plan(tenant.plan_id)

    monthly_limit = (
        plan_info.pruebas_monthly_docs_limit
        if tenant.sri_environment == SriEnvironment.TESTING
        else plan_info.document_limit
    )

    serie = body.establishment_code + body.emission_point_code

    lines = [
        CreditNoteLineData(parent_line_index=ln.parent_line_index, quantity=ln.quantity)
        for ln in body.lines
    ]

    repo = _repo()
    seq_port = _sequences_port()

    document, is_full_annulment = EmitCreditNoteUseCase(repo, seq_port).execute(
        EmitCreditNoteCommand(
            tenant_id=tenant_id,
            ruc=tenant.ruc,
            sri_environment=tenant.sri_environment.value,
            certificate_secret_arn=tenant.certificate_secret_arn,
            monthly_limit=monthly_limit,
            serie=serie,
            issued_at=body.issued_at,
            related_document_id=body.related_document_id,
            credit_note_reason=body.credit_note_reason,
            lines=lines,
            created_by=request.user_id,
        )
    )

    response = _finalize_emission(document, request, repo)

    if is_full_annulment:
        # Best-effort: mismo nivel de tolerancia que _send_sign_message — es una mejora
        # de UX (banner + bloqueo de doble anulacion), no debe tumbar la respuesta 202 si
        # falla. EmitCreditNoteUseCase ya valido que no exista una anulacion previa.
        try:
            repo.mark_annulled_by_credit_note(
                tenant_id, body.related_document_id, credit_note_id=document.document_id
            )
        except Exception:
            _log.warning(
                "failed to mark parent invoice as annulled_by_credit_note",
                document_id=document.document_id,
                related_document_id=body.related_document_id,
            )

    return response


def _finalize_emission(
    document,
    request: Request,
    repo: DynamoDocumentsRepository,
    *,
    override_reason: str | None = None,
) -> dict:
    response = ApiResponse.accepted(
        {
            "document_id": document.document_id,
            "access_key": document.access_key,
            "sequential": document.sequential,
            "sequential_display": document.sequential_display,
            "status": DocumentStatus.PENDING.value,
        },
        request.request_id,
    )

    repo.save(
        document,
        idempotency=require_current_context(),
        response=response,
        override_reason=override_reason,
        user_id=request.user_id,
    )

    try:
        _send_sign_message(document.document_id, document.tenant_id)
    except Exception:
        _log.warning(
            "SQS send_message failed after document save (document stuck PENDING)",
            document_id=document.document_id,
        )

    return response


@lambda_handler
@require_role("owner", "admin", "viewer", "superadmin")
def _list(request: Request, context) -> dict:
    tenant_id = _resolve_tenant_id(request)
    params = parse(ListDocumentsQueryParams, request.query_params)

    use_case = ListDocumentsUseCase(_repo())
    command = ListDocumentsCommand(
        tenant_id=tenant_id,
        status=params.status,
        doc_type=params.doc_type,
        serie=params.serie,
        q=params.q,
        date_from=params.date_from,
        date_to=params.date_to,
        limit=params.limit,
        cursor=params.cursor,
    )
    documents, next_cursor = use_case.execute(command)
    return ApiResponse.paginated(
        items=[d.to_dict() for d in documents],
        next_token=next_cursor,
        request_id=request.request_id,
        total=use_case.count(command),
    )


def _resolve_monthly_limit(tenant_id: str) -> tuple[int | None, bool]:
    """None when the tenant's plan can't be resolved (eg. deactivated by superadmin
    after the tenant subscribed) — the summary still returns counts, just without the
    limit comparison, instead of failing the whole dashboard block."""
    try:
        tenant = _get_tenant(tenant_id)
        plan_info = _get_plan(tenant.plan_id)
    except ValidationError:
        _log.warning("could not resolve plan for documents summary limit", tenant_id=tenant_id)
        return None, False

    limit = (
        plan_info.pruebas_monthly_docs_limit
        if tenant.sri_environment == SriEnvironment.TESTING
        else plan_info.document_limit
    )
    return limit, plan_info.is_free


@lambda_handler
@require_role("owner", "admin", "viewer", "superadmin")
def _summary(request: Request, context) -> dict:
    tenant_id = _resolve_tenant_id(request)
    monthly_limit, is_free_plan = _resolve_monthly_limit(tenant_id)
    summary = GetDocumentsSummaryUseCase(_repo()).execute(
        tenant_id,
        monthly_limit,
        is_free_plan=is_free_plan,
    )
    return ApiResponse.ok(summary.to_dict(), request.request_id)


@lambda_handler
@require_role("owner", "admin", "viewer", "superadmin")
def _get(request: Request, context) -> dict:
    tenant_id = _resolve_tenant_id(request)
    document_id = require_path_param(request, "id")

    document = GetDocumentUseCase(_repo()).execute(
        GetDocumentCommand(tenant_id=tenant_id, document_id=document_id)
    )
    return ApiResponse.ok(document.to_dict(), request.request_id)


@lambda_handler
@require_role("owner", "admin", "viewer", "superadmin")
def _get_ride(request: Request, context) -> dict:
    tenant_id = _resolve_tenant_id(request)
    document_id = require_path_param(request, "id")

    url = GetRideUrlUseCase(_repo()).execute(
        GetRideUrlCommand(
            tenant_id=tenant_id,
            document_id=document_id,
            documents_bucket=_documents_bucket,
        )
    )
    return ApiResponse.ok({"url": url}, request.request_id)


@lambda_handler
@require_role("owner", "admin", "viewer", "superadmin")
def _get_xml(request: Request, context) -> dict:
    tenant_id = _resolve_tenant_id(request)
    document_id = require_path_param(request, "id")

    url = GetXmlUrlUseCase(_repo()).execute(
        GetXmlUrlCommand(
            tenant_id=tenant_id,
            document_id=document_id,
            documents_bucket=_documents_bucket,
        )
    )
    return ApiResponse.ok({"url": url}, request.request_id)


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _annul(request: Request, context) -> dict:
    tenant_id = _resolve_tenant_id(request)
    document_id = require_path_param(request, "id")
    body = parse(AnnulDocumentRequest, request.body)
    repo = _repo()

    document = AnnulDocumentUseCase(repo).execute(
        AnnulDocumentCommand(
            tenant_id=tenant_id,
            document_id=document_id,
            reason=body.reason,
            user_id=request.user_id,
        )
    )

    response = ApiResponse.ok(document.to_dict(), request.request_id)

    repo.annul(
        tenant_id,
        document_id,
        reason=body.reason,
        user_id=request.user_id,
        access_key=document.access_key,
        idempotency=require_current_context(),
        response=response,
    )

    return response


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _retry(request: Request, context) -> dict:
    """POST /documents/{id}/retry — reenvia un documento REJECTED reusando la misma
    clave de acceso/secuencial (ver RetryDocumentUseCase). Reusa _send_sign_message: el
    reintento vuelve a pasar por SIGN, no por POLL.
    """
    tenant_id = _resolve_tenant_id(request)
    document_id = require_path_param(request, "id")
    repo = _repo()

    document = RetryDocumentUseCase(repo).execute(
        RetryDocumentCommand(
            tenant_id=tenant_id,
            document_id=document_id,
            user_id=request.user_id,
        )
    )

    response = ApiResponse.ok(document.to_dict(), request.request_id)

    repo.retry(
        tenant_id,
        document_id,
        user_id=request.user_id,
        access_key=document.access_key,
        idempotency=require_current_context(),
        response=response,
    )

    try:
        _send_sign_message(document.document_id, document.tenant_id)
    except Exception:
        _log.warning(
            "SQS send_message failed after document retry (document stuck PENDING)",
            document_id=document.document_id,
        )

    return response


# ── Entry point ───────────────────────────────────────────────────────────────

_DOCUMENTS_PATTERN = re.compile(r"^/documents$")
_DOCUMENTS_SUMMARY_PATTERN = re.compile(r"^/documents/summary$")
_DOCUMENT_PATTERN = re.compile(r"^/documents/[^/]+$")
_RIDE_PATTERN = re.compile(r"^/documents/[^/]+/ride$")
_XML_PATTERN = re.compile(r"^/documents/[^/]+/xml$")
_ANNUL_PATTERN = re.compile(r"^/documents/[^/]+/annul$")
_RETRY_PATTERN = re.compile(r"^/documents/[^/]+/retry$")


def handler(event: dict, context) -> dict:
    ctx = event.get("requestContext", {})
    method = ctx.get("http", {}).get("method", "")
    path = ctx.get("http", {}).get("path", "")
    # Strip query string from path if present
    path = path.split("?")[0]

    if _DOCUMENTS_PATTERN.match(path):
        if method == "POST":
            return _emit(event, context)
        if method == "GET":
            return _list(event, context)

    if _DOCUMENTS_SUMMARY_PATTERN.match(path):
        if method == "GET":
            return _summary(event, context)

    if _RIDE_PATTERN.match(path):
        if method == "GET":
            return _get_ride(event, context)

    if _XML_PATTERN.match(path):
        if method == "GET":
            return _get_xml(event, context)

    if _ANNUL_PATTERN.match(path):
        if method == "POST":
            return _annul(event, context)

    if _RETRY_PATTERN.match(path):
        if method == "POST":
            return _retry(event, context)

    if _DOCUMENT_PATTERN.match(path):
        if method == "GET":
            return _get(event, context)

    return ApiResponse.error(DocumentNotFoundError(), ctx.get("requestId", "local"))
