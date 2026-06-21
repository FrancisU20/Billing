from __future__ import annotations

from shared.errors import AppError, BusinessError, NotFoundError


class FreePlanPaymentError(BusinessError):
    code = "FREE_PLAN_NO_PAYMENT"
    default_message = "El plan gratuito no requiere pago."


class CustomQuotePlanPaymentError(BusinessError):
    code = "CUSTOM_QUOTE_PLAN_NO_PAYMENT"
    default_message = "Este plan es a medida — contacta a ventas en vez de pagar en línea."


class PlanNotFoundForPaymentError(NotFoundError):
    code = "PLAN_NOT_FOUND"
    default_message = "Plan no encontrado."


class PaymentNotFoundError(NotFoundError):
    code = "PAYMENT_NOT_FOUND"
    default_message = "Pago no encontrado."


class PaymentAlreadyConfirmedError(AppError):
    code = "PAYMENT_ALREADY_CONFIRMED"
    default_message = "El pago ya fue procesado."
    status_code = 409


class PaymentCreationError(AppError):
    code = "PAYMENT_CREATION_FAILED"
    default_message = "No se pudo crear la orden de pago."
    status_code = 502


class PaymentConfirmError(AppError):
    code = "PAYMENT_CONFIRM_FAILED"
    default_message = "No se pudo confirmar el pago."
    status_code = 502


class PaymentNotRefundableError(AppError):
    code = "PAYMENT_NOT_REFUNDABLE"
    default_message = "Solo se pueden reembolsar pagos confirmados (PAID)."
    status_code = 409


class PaymentRefundError(AppError):
    code = "PAYMENT_REFUND_FAILED"
    default_message = "No se pudo procesar el reembolso."
    status_code = 502
