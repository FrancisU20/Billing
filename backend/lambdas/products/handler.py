from __future__ import annotations

"""
Products Lambda — tenant product/service catalog.

Routes:
    POST   /products                    create product   (owner | admin)
    GET    /products                    list products     (owner | admin | viewer)
    GET    /products/{id}                get by ID         (owner | admin | viewer)
    PATCH  /products/{id}                update             (owner | admin)
    DELETE /products/{id}                soft delete       (owner | admin)
    GET    /products/discount-campaign   get campaign       (owner | admin | viewer)
    PUT    /products/discount-campaign   upsert campaign    (owner | admin)
"""

import re

from lambdas._base.handler import lambda_handler
from lambdas._base.idempotency import idempotent, require_current_context
from lambdas._base.parser import Request, parse, require_path_param
from lambdas._base.permissions import require_role
from lambdas._base.response import ApiResponse
from lambdas.products.domain.commands import CreateProductCommand, UpdateProductCommand
from lambdas.products.domain.enums import ProductKind, ProductStatus
from lambdas.products.infra.discount_campaign_repository import (
    DynamoDiscountCampaignRepository,
)
from lambdas.products.infra.product_repository import DynamoProductRepository
from lambdas.products.schemas import (
    CreateProductRequest,
    UpdateDiscountCampaignRequest,
    UpdateProductRequest,
)
from lambdas.products.use_cases.create_product import CreateProductUseCase
from lambdas.products.use_cases.delete_product import DeleteProductUseCase
from lambdas.products.use_cases.get_discount_campaign import GetDiscountCampaignUseCase
from lambdas.products.use_cases.get_product import GetProductUseCase
from lambdas.products.use_cases.list_products import ListProductsQuery, ListProductsUseCase
from lambdas.products.use_cases.update_discount_campaign import UpdateDiscountCampaignUseCase
from lambdas.products.use_cases.update_product import UpdateProductUseCase
from shared.config import env
from shared.db.client import get_table
from shared.db.limits import DEFAULT_LIST_LIMIT, clamp_list_limit
from shared.errors import MissingTenantContextError, NotFoundError, ValidationError

_TABLE = get_table("PRODUCTS_TABLE")
_AUDIT_TABLE = get_table("AUDIT_LOG_TABLE") if env("AUDIT_LOG_TABLE", "") else None


def _repo(request: Request) -> DynamoProductRepository:
    if not request.tenant_id:
        raise MissingTenantContextError()
    return DynamoProductRepository(request.tenant_id, _TABLE, _AUDIT_TABLE)


def _campaign_repo(request: Request) -> DynamoDiscountCampaignRepository:
    if not request.tenant_id:
        raise MissingTenantContextError()
    return DynamoDiscountCampaignRepository(request.tenant_id, _TABLE, _AUDIT_TABLE)


def _parse_list_query(params: dict) -> ListProductsQuery:
    try:
        limit = int(params.get("limit", DEFAULT_LIST_LIMIT))
    except (TypeError, ValueError) as exc:
        raise ValidationError("limit debe ser un número entero") from exc
    if limit < 1:
        raise ValidationError("limit debe ser mayor a cero")

    status = params.get("status")
    if status:
        try:
            ProductStatus(status)
        except ValueError as exc:
            raise ValidationError("Estado inválido") from exc

    kind = params.get("kind")
    if kind:
        try:
            ProductKind(kind)
        except ValueError as exc:
            raise ValidationError("Tipo de producto inválido") from exc

    return ListProductsQuery(
        limit=clamp_list_limit(limit),
        next_token=params.get("next_token"),
        status=status,
        kind=kind,
        q=params.get("q"),
        sku=params.get("sku"),
    )


@lambda_handler
@require_role("owner", "admin")
@idempotent
def _create(request: Request, context) -> dict:
    body = parse(CreateProductRequest, request.body)
    repo = _repo(request)
    product = CreateProductUseCase(repo).execute(
        CreateProductCommand(
            tenant_id=request.tenant_id,
            sku=body.sku,
            name=body.name,
            description=body.description,
            kind=body.kind,
            unit=body.unit,
            unit_price=body.unit_price,
            iva_rate=body.iva_rate,
            discount_percentage=body.discount_percentage,
            stock_enabled=body.stock_enabled,
            stock_quantity=body.stock_quantity,
            low_stock_threshold=body.low_stock_threshold,
            created_by=request.user_id,
        )
    )
    response = ApiResponse.created(product.to_dict(), request.request_id)
    repo.commit(
        product=product,
        user_id=request.user_id,
        action="CREATE",
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_role("owner", "admin", "viewer")
def _list(request: Request, context) -> dict:
    query = _parse_list_query(request.query_params)
    use_case = ListProductsUseCase(_repo(request))
    products, next_token = use_case.execute(query)
    return ApiResponse.paginated(
        items=[p.to_dict() for p in products],
        next_token=next_token,
        request_id=request.request_id,
        total=use_case.count(query),
    )


@lambda_handler
@require_role("owner", "admin", "viewer")
def _get(request: Request, context) -> dict:
    product_id = require_path_param(request, "id")
    product = GetProductUseCase(_repo(request)).execute(product_id)
    return ApiResponse.ok(product.to_dict(), request.request_id)


@lambda_handler
@require_role("owner", "admin")
@idempotent
def _update(request: Request, context) -> dict:
    product_id = require_path_param(request, "id")
    body = parse(UpdateProductRequest, request.body)
    repo = _repo(request)
    product = UpdateProductUseCase(repo).execute(
        UpdateProductCommand(
            product_id=product_id,
            sku=body.sku,
            name=body.name,
            description=body.description,
            kind=body.kind,
            unit=body.unit,
            unit_price=body.unit_price,
            iva_rate=body.iva_rate,
            discount_percentage=body.discount_percentage,
            stock_enabled=body.stock_enabled,
            stock_quantity=body.stock_quantity,
            low_stock_threshold=body.low_stock_threshold,
            status=body.status,
            updated_by=request.user_id,
        )
    )
    response = ApiResponse.ok(product.to_dict(), request.request_id)
    repo.commit(
        product=product,
        user_id=request.user_id,
        action="UPDATE",
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_role("owner", "admin")
@idempotent
def _delete(request: Request, context) -> dict:
    product_id = require_path_param(request, "id")
    repo = _repo(request)
    product = DeleteProductUseCase(repo).execute(product_id, request.user_id)
    response = ApiResponse.no_content(request.request_id)
    repo.commit(
        product=product,
        user_id=request.user_id,
        action="DELETE",
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_role("owner", "admin", "viewer")
def _get_discount_campaign(request: Request, context) -> dict:
    campaign = GetDiscountCampaignUseCase(_campaign_repo(request)).execute()
    return ApiResponse.ok(campaign.to_dict(), request.request_id)


@lambda_handler
@require_role("owner", "admin")
@idempotent
def _update_discount_campaign(request: Request, context) -> dict:
    body = parse(UpdateDiscountCampaignRequest, request.body)
    repo = _campaign_repo(request)
    campaign = UpdateDiscountCampaignUseCase(repo).execute(
        active=body.active,
        percentage=body.percentage,
        updated_by=request.user_id,
    )
    response = ApiResponse.ok(campaign.to_dict(), request.request_id)
    repo.save(
        campaign=campaign,
        user_id=request.user_id,
        action="UPSERT",
        idempotency=require_current_context(),
        response=response,
    )
    return response


_ID_PATTERN = re.compile(r"^/products/[^/]+$")
_DISCOUNT_CAMPAIGN_PATH = "/products/discount-campaign"


def handler(event: dict, context) -> dict:
    ctx = event.get("requestContext", {})
    method = ctx.get("http", {}).get("method", "")
    path = ctx.get("http", {}).get("path", "")

    if path == "/products":
        if method == "POST":
            return _create(event, context)
        if method == "GET":
            return _list(event, context)

    if path == _DISCOUNT_CAMPAIGN_PATH:
        if method == "GET":
            return _get_discount_campaign(event, context)
        if method == "PUT":
            return _update_discount_campaign(event, context)

    if _ID_PATTERN.match(path):
        if method == "GET":
            return _get(event, context)
        if method == "PATCH":
            return _update(event, context)
        if method == "DELETE":
            return _delete(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
