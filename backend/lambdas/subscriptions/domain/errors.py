from __future__ import annotations

from shared.errors import AppError, BusinessError, NotFoundError


class FreePlanPaymentError(BusinessError):
    code = "FREE_PLAN_NO_PAYMENT"
    default_message = "El plan gratuito no requiere pago."


class PlanNotFoundForPaymentError(NotFoundError):
    code = "PLAN_NOT_FOUND"
    default_message = "Plan no encontrado."


class PaymentNotFoundError(NotFoundError):
    code = "PAYMENT_NOT_FOUND"
    default_message = "Pago no encontrado."


class PaymentAlreadyCapturedError(AppError):
    code = "PAYMENT_ALREADY_CAPTURED"
    default_message = "El pago ya fue procesado."
    status_code = 409


class PaymentCreationError(AppError):
    code = "PAYMENT_CREATION_FAILED"
    default_message = "No se pudo crear la orden de pago."
    status_code = 502


class PaymentCaptureError(AppError):
    code = "PAYMENT_CAPTURE_FAILED"
    default_message = "No se pudo procesar el pago."
    status_code = 502
