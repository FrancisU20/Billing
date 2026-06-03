"""
Cliente SOAP para los servicios del SRI Ecuador.
Servicios: RecepcionComprobantesOffline, AutorizacionComprobantesOffline
"""
import base64
import time
from dataclasses import dataclass

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from zeep import Client
from zeep.transports import Transport

ENDPOINTS = {
    "PRUEBAS": {
        "recepcion": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
        "autorizacion": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
    },
    "PRODUCCION": {
        "recepcion": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
        "autorizacion": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
    },
}

TIMEOUT_SECONDS = 30


@dataclass
class RespuestaRecepcion:
    estado: str       # RECIBIDA | DEVUELTA
    comprobantes: list[dict]
    raw: dict


@dataclass
class RespuestaAutorizacion:
    numero_autorizacion: str | None
    fecha_autorizacion: str | None
    estado: str       # AUTORIZADO | NO AUTORIZADO | EN PROCESO
    mensajes: list[dict]
    raw: dict


def _make_transport() -> Transport:
    session = Session()
    retry = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return Transport(session=session, timeout=TIMEOUT_SECONDS)


def enviar_comprobante(xml_firmado: str, ambiente: str) -> RespuestaRecepcion:
    """Envía un XML firmado al servicio de recepción del SRI."""
    wsdl = ENDPOINTS[ambiente]["recepcion"]
    client = Client(wsdl=wsdl, transport=_make_transport())

    xml_b64 = base64.b64encode(xml_firmado.encode("utf-8")).decode("ascii")

    inicio = time.time()
    response = client.service.validarComprobante(xml_b64)
    duracion_ms = int((time.time() - inicio) * 1000)

    raw = {"duracion_ms": duracion_ms, "response": str(response)}

    estado = getattr(response, "estado", "DESCONOCIDO")
    comprobantes = []
    if hasattr(response, "comprobantes") and response.comprobantes:
        for comp in response.comprobantes.comprobante or []:
            mensajes = []
            if hasattr(comp, "mensajes") and comp.mensajes:
                for m in comp.mensajes.mensaje or []:
                    mensajes.append({
                        "identificador": getattr(m, "identificador", ""),
                        "mensaje": getattr(m, "mensaje", ""),
                        "informacionAdicional": getattr(m, "informacionAdicional", ""),
                        "tipo": getattr(m, "tipo", ""),
                    })
            comprobantes.append({
                "claveAcceso": getattr(comp, "claveAcceso", ""),
                "estado": getattr(comp, "estado", ""),
                "mensajes": mensajes,
            })

    return RespuestaRecepcion(estado=estado, comprobantes=comprobantes, raw=raw)


def consultar_autorizacion(clave_acceso: str, ambiente: str) -> RespuestaAutorizacion:
    """Consulta el estado de autorización de un comprobante por clave de acceso."""
    wsdl = ENDPOINTS[ambiente]["autorizacion"]
    client = Client(wsdl=wsdl, transport=_make_transport())

    inicio = time.time()
    response = client.service.autorizacionComprobante(clave_acceso)
    duracion_ms = int((time.time() - inicio) * 1000)

    raw = {"duracion_ms": duracion_ms}

    numero_autorizacion = None
    fecha_autorizacion = None
    estado = "EN PROCESO"
    mensajes = []

    autorizaciones = getattr(response, "autorizaciones", None)
    if autorizaciones:
        autz_list = getattr(autorizaciones, "autorizacion", []) or []
        if autz_list:
            autz = autz_list[0]
            numero_autorizacion = str(getattr(autz, "numeroAutorizacion", "") or "")
            fecha_dt = getattr(autz, "fechaAutorizacion", None)
            fecha_autorizacion = str(fecha_dt) if fecha_dt else None
            estado = str(getattr(autz, "estado", "EN PROCESO"))

            msgs = getattr(autz, "mensajes", None)
            if msgs:
                for m in getattr(msgs, "mensaje", []) or []:
                    mensajes.append({
                        "identificador": str(getattr(m, "identificador", "")),
                        "mensaje": str(getattr(m, "mensaje", "")),
                        "informacionAdicional": str(getattr(m, "informacionAdicional", "")),
                        "tipo": str(getattr(m, "tipo", "")),
                    })

    return RespuestaAutorizacion(
        numero_autorizacion=numero_autorizacion,
        fecha_autorizacion=fecha_autorizacion,
        estado=estado,
        mensajes=mensajes,
        raw=raw,
    )
