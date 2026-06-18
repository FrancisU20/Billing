from __future__ import annotations

import unittest

from lambdas.invoice_processor.sri_client import SriSoapClient
from shared.errors import ExternalServiceError


class FakeResponse:
    def __init__(self, status: int, data: bytes) -> None:
        self.status = status
        self.data = data


class FakeHttp:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict] = []

    def request(self, method, url, *, body, headers):
        self.calls.append({"method": method, "url": url, "body": body, "headers": headers})
        return self.response


def _envelope(inner: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        f"<soap:Body>{inner}</soap:Body></soap:Envelope>"
    ).encode()


class SriSoapClientTests(unittest.TestCase):
    def test_recepcion_sends_empty_soap_action(self) -> None:
        # El servicio del SRI rutea por el nombre de operación en el body, no por
        # SOAPAction — cualquier valor no vacío responde 500 ("does not match an
        # operation"), confirmado a mano contra celcer.sri.gob.ec.
        body = _envelope(
            '<ns2:validarComprobanteResponse xmlns:ns2="http://ec.gob.sri.ws.recepcion">'
            "<RespuestaRecepcionComprobante><estado>RECIBIDA</estado></RespuestaRecepcionComprobante>"
            "</ns2:validarComprobanteResponse>"
        )
        http = FakeHttp(FakeResponse(200, body))
        client = SriSoapClient(http=http)

        client.recepcion(environment="testing", xmls=["<factura/>"])

        self.assertEqual(http.calls[0]["headers"]["SOAPAction"], '""')

    def test_autorizacion_sends_empty_soap_action(self) -> None:
        body = _envelope(
            '<ns2:autorizacionComprobanteResponse xmlns:ns2="http://ec.gob.sri.ws.autorizacion">'
            "<RespuestaAutorizacionComprobante><autorizaciones>"
            "<autorizacion><estado>EN PROCESO</estado></autorizacion>"
            "</autorizaciones></RespuestaAutorizacionComprobante>"
            "</ns2:autorizacionComprobanteResponse>"
        )
        http = FakeHttp(FakeResponse(200, body))
        client = SriSoapClient(http=http)

        client.autorizacion(environment="testing", access_key="1" * 49)

        self.assertEqual(http.calls[0]["headers"]["SOAPAction"], '""')

    def test_recepcion_received(self) -> None:
        body = _envelope(
            '<ns2:validarComprobanteResponse xmlns:ns2="http://ec.gob.sri.ws.recepcion">'
            "<RespuestaRecepcionComprobante><estado>RECIBIDA</estado></RespuestaRecepcionComprobante>"
            "</ns2:validarComprobanteResponse>"
        )
        client = SriSoapClient(http=FakeHttp(FakeResponse(200, body)))

        result = client.recepcion(environment="testing", xmls=["<factura/>"])

        self.assertTrue(result.received)
        self.assertEqual(result.errors, [])

    def test_recepcion_devuelta_with_errors(self) -> None:
        body = _envelope(
            '<ns2:validarComprobanteResponse xmlns:ns2="http://ec.gob.sri.ws.recepcion">'
            "<RespuestaRecepcionComprobante><estado>DEVUELTA</estado>"
            "<comprobantes><comprobante><mensajes><mensaje>"
            "<identificador>35</identificador><mensaje>ARCHIVO NO CUMPLE ESTRUCTURA XML</mensaje>"
            "</mensaje></mensajes></comprobante></comprobantes>"
            "</RespuestaRecepcionComprobante></ns2:validarComprobanteResponse>"
        )
        client = SriSoapClient(http=FakeHttp(FakeResponse(200, body)))

        result = client.recepcion(environment="testing", xmls=["<factura/>"])

        self.assertFalse(result.received)
        self.assertEqual(result.errors[0].code, "35")

    def test_autorizacion_autorizado(self) -> None:
        body = _envelope(
            '<ns2:autorizacionComprobanteResponse xmlns:ns2="http://ec.gob.sri.ws.autorizacion">'
            "<RespuestaAutorizacionComprobante><autorizaciones><autorizacion>"
            "<estado>AUTORIZADO</estado><numeroAutorizacion>123</numeroAutorizacion>"
            "<fechaAutorizacion>2026-06-18T10:00:00</fechaAutorizacion>"
            "<comprobante>&lt;factura/&gt;</comprobante>"
            "</autorizacion></autorizaciones></RespuestaAutorizacionComprobante>"
            "</ns2:autorizacionComprobanteResponse>"
        )
        client = SriSoapClient(http=FakeHttp(FakeResponse(200, body)))

        result = client.autorizacion(environment="testing", access_key="1" * 49)

        self.assertEqual(result.status, "AUTORIZADO")
        self.assertEqual(result.authorization_number, "123")
        self.assertEqual(result.signed_xml, "<factura/>")

    def test_autorizacion_en_proceso(self) -> None:
        body = _envelope(
            '<ns2:autorizacionComprobanteResponse xmlns:ns2="http://ec.gob.sri.ws.autorizacion">'
            "<RespuestaAutorizacionComprobante><autorizaciones>"
            "<autorizacion><estado>EN PROCESO</estado></autorizacion>"
            "</autorizaciones></RespuestaAutorizacionComprobante>"
            "</ns2:autorizacionComprobanteResponse>"
        )
        client = SriSoapClient(http=FakeHttp(FakeResponse(200, body)))

        result = client.autorizacion(environment="testing", access_key="1" * 49)

        self.assertEqual(result.status, "EN_PROCESO")

    def test_soap_fault_raises_retryable_error(self) -> None:
        body = _envelope(
            "<soap:Fault><faultcode>soap:Server</faultcode>"
            "<faultstring>javax.persistence.EntityNotFoundException</faultstring></soap:Fault>"
        )
        client = SriSoapClient(http=FakeHttp(FakeResponse(200, body)))

        with self.assertRaises(ExternalServiceError):
            client.autorizacion(environment="testing", access_key="1" * 49)

    def test_5xx_raises_external_service_error(self) -> None:
        client = SriSoapClient(http=FakeHttp(FakeResponse(500, b"")))

        with self.assertRaises(ExternalServiceError):
            client.recepcion(environment="testing", xmls=["<factura/>"])


if __name__ == "__main__":
    unittest.main()
