from __future__ import annotations

"""
SOAP client for the SRI Ecuador "Offline" webservices.

Plain SOAP 1.1 envelopes over `urllib3` (same HTTP client already used by
`BrevoEmailSender` — no new HTTP dependency). No WSDL/zeep: the SRI WSDL has been
historically unreliable to fetch at runtime, and the operations are simple enough
(one string param in, one XML response) that a hand-built envelope is more robust.

Response parsing (`estado`/`mensaje` element names and values) follows the public
Ficha Técnica. This is the module most likely to need small adjustments after the
first real run against the SRI testing webservice (`celcer.sri.gob.ec`) — isolated
here on purpose so a fix doesn't ripple into the use cases.
"""

import base64

import urllib3
from lxml import etree

from lambdas.invoice_processor.ports import (
    AutorizacionResult,
    ISriClient,
    RecepcionResult,
    SriErrorDetail,
)
from shared.errors import ExternalServiceError
from shared.logger import get_logger

_log = get_logger(__name__)

_RECEPCION_URL = {
    "testing": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline",
    "production": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline",
}
_AUTORIZACION_URL = {
    "testing": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline",
    "production": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline",
}

_SOAP_ENVELOPE_NS = "http://schemas.xmlsoap.org/soap/envelope/"
_RECEPCION_NS = "http://ec.gob.sri.ws.recepcion"
_AUTORIZACION_NS = "http://ec.gob.sri.ws.autorizacion"

_REQUEST_TIMEOUT = urllib3.Timeout(connect=10, read=60)
_NS = {"soapenv": _SOAP_ENVELOPE_NS}


class SriSoapClient(ISriClient):
    def __init__(self, http: urllib3.PoolManager | None = None) -> None:
        self._http = http or urllib3.PoolManager(timeout=_REQUEST_TIMEOUT)

    def recepcion(self, *, environment: str, xmls: list[str]) -> RecepcionResult:
        xml_b64 = base64.b64encode(xmls[0].encode("utf-8")).decode("ascii")
        envelope = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<soapenv:Envelope xmlns:soapenv="{_SOAP_ENVELOPE_NS}" xmlns:ec="{_RECEPCION_NS}">'
            "<soapenv:Body><ec:validarComprobante>"
            f"<xml>{xml_b64}</xml>"
            "</ec:validarComprobante></soapenv:Body></soapenv:Envelope>"
        )
        body = self._post(_RECEPCION_URL[environment], envelope, "validarComprobante")
        return self._parse_recepcion(body)

    def autorizacion(self, *, environment: str, access_key: str) -> AutorizacionResult:
        envelope = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<soapenv:Envelope xmlns:soapenv="{_SOAP_ENVELOPE_NS}" xmlns:ec="{_AUTORIZACION_NS}">'
            "<soapenv:Body><ec:autorizacionComprobante>"
            f"<claveAccesoComprobante>{access_key}</claveAccesoComprobante>"
            "</ec:autorizacionComprobante></soapenv:Body></soapenv:Envelope>"
        )
        body = self._post(_AUTORIZACION_URL[environment], envelope, "autorizacionComprobante")
        return self._parse_autorizacion(body)

    def _post(self, url: str, envelope: str, operation: str) -> bytes:
        try:
            response = self._http.request(
                "POST",
                url,
                body=envelope.encode("utf-8"),
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    # El servicio del SRI rutea por el nombre de la operación en el
                    # body, no por SOAPAction — cualquier valor no vacío (incluido
                    # "{url}#{operation}") responde 500 con el fault "The given
                    # SOAPAction ... does not match an operation." Confirmado a mano
                    # contra celcer.sri.gob.ec (ambiente de pruebas).
                    "SOAPAction": '""',
                },
            )
        except urllib3.exceptions.HTTPError as exc:
            _log.error("SRI SOAP request failed", operation=operation, error=str(exc))
            raise ExternalServiceError("el SRI no respondió") from exc

        if response.status >= 500:
            _log.error(
                "SRI SOAP 5xx response",
                operation=operation,
                status=response.status,
                body=response.data.decode("utf-8", errors="replace")[:2000],
            )
            raise ExternalServiceError("el SRI respondió con error de servidor")

        return response.data

    def _parse_recepcion(self, body: bytes) -> RecepcionResult:
        root = self._parse_body(body)
        estado = root.findtext(".//estado") or ""
        errors = [
            SriErrorDetail(
                code=msg.findtext("identificador") or "",
                message=msg.findtext("mensaje") or "",
            )
            for msg in root.iter("mensaje")
        ]
        return RecepcionResult(received=(estado == "RECIBIDA"), errors=errors)

    def _parse_autorizacion(self, body: bytes) -> AutorizacionResult:
        root = self._parse_body(body)
        estado = root.findtext(".//autorizacion/estado") or root.findtext(".//estado") or ""
        if estado == "AUTORIZADO":
            return AutorizacionResult(
                status="AUTORIZADO",
                authorization_number=root.findtext(".//numeroAutorizacion"),
                authorized_at=root.findtext(".//fechaAutorizacion"),
                signed_xml=root.findtext(".//comprobante"),
            )
        if estado == "EN PROCESO":
            return AutorizacionResult(status="EN_PROCESO")
        errors = [
            SriErrorDetail(
                code=msg.findtext("identificador") or "",
                message=msg.findtext("mensaje") or "",
            )
            for msg in root.iter("mensaje")
        ]
        return AutorizacionResult(status="RECHAZADO", errors=errors)

    def _parse_body(self, body: bytes) -> etree._Element:
        try:
            envelope = etree.fromstring(body)  # noqa: S320 - fixed SRI government webservice over HTTPS, not user-controlled input
        except etree.XMLSyntaxError as exc:
            _log.error("SRI SOAP response malformed XML")
            raise ExternalServiceError("respuesta del SRI malformada") from exc
        soap_body = envelope.find("soapenv:Body", _NS)
        if soap_body is None or len(soap_body) == 0:
            raise ExternalServiceError("respuesta del SRI vacía")
        content = soap_body[0]
        # Un soap:Fault (ej. error interno del SRI, documento aún no indexado en
        # AutorizacionComprobantesOffline) no es un estado de negocio — sin esto,
        # el resto del parser lo confundiría silenciosamente con un estado vacío.
        if content.tag.endswith("Fault"):
            faultstring = content.findtext("faultstring") or "fault sin detalle"
            _log.error("SRI SOAP fault", faultstring=faultstring)
            raise ExternalServiceError(f"el SRI devolvió un fault: {faultstring}")
        return content
