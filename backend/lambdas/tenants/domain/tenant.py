"""
Entidad Tenant — empresa que usa el SaaS de facturación.

Hereda GlobalEntity (no TenantScopedEntity) porque el tenant
ES la raíz del sistema, no pertenece a otro tenant.

Toda validación de negocio vive aquí — las RUC, Email son value objects
que lanzan ValidationError si el dato es inválido.
"""
from dataclasses import dataclass, field

from shared.domain.base_entity import GlobalEntity
from shared.domain.value_objects.email import Email
from shared.domain.value_objects.ruc import RUC

from lambdas.tenants.domain.commands import CreateTenantCommand, UpdateTenantCommand
from lambdas.tenants.domain.enums import AmbienteSri, EstadoTenant
from lambdas.tenants.domain.errors import AmbienteSriInvalidoError


@dataclass
class Tenant(GlobalEntity):
    ruc:              str = ""
    nombre_comercial: str = ""
    nombre_rep_legal: str = ""
    email:            str = ""
    telefono:         str = ""
    direccion:        str = ""
    ambiente_sri:     AmbienteSri  = field(default=AmbienteSri.PRUEBAS)
    estado:           EstadoTenant = field(default=EstadoTenant.ACTIVO)
    plan:             str = "basico"

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(cls, cmd: CreateTenantCommand) -> "Tenant":
        ruc   = RUC(cmd.ruc)     # lanza ValidationError si RUC inválido
        email = Email(cmd.email) # lanza ValidationError si email inválido
        return cls(
            ruc              = str(ruc),
            nombre_comercial = cmd.nombre_comercial.strip(),
            nombre_rep_legal = cmd.nombre_rep_legal.strip(),
            email            = str(email),
            telefono         = cmd.telefono.strip(),
            direccion        = cmd.direccion.strip(),
            ambiente_sri     = AmbienteSri.PRUEBAS,  # siempre inicia en pruebas
            estado           = EstadoTenant.ACTIVO,
            plan             = cmd.plan,
            created_by       = cmd.created_by,
            updated_by       = cmd.created_by,
        )

    # ── comportamiento de dominio ─────────────────────────────────────────────

    def update(self, cmd: UpdateTenantCommand) -> None:
        if cmd.nombre_comercial is not None:
            self.nombre_comercial = cmd.nombre_comercial.strip()
        if cmd.nombre_rep_legal is not None:
            self.nombre_rep_legal = cmd.nombre_rep_legal.strip()
        if cmd.email is not None:
            self.email = str(Email(cmd.email))
        if cmd.telefono is not None:
            self.telefono = cmd.telefono.strip()
        if cmd.direccion is not None:
            self.direccion = cmd.direccion.strip()
        if cmd.ambiente_sri is not None:
            try:
                self.ambiente_sri = AmbienteSri(cmd.ambiente_sri)
            except ValueError:
                raise AmbienteSriInvalidoError()
        self.touch(cmd.updated_by)

    def cambiar_estado(self, nuevo_estado: EstadoTenant, updated_by: str) -> None:
        self.estado = nuevo_estado
        self.touch(updated_by)

    def es_activo(self) -> bool:
        return self.estado == EstadoTenant.ACTIVO

    # ── serialización ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "ruc":              self.ruc,
            "nombre_comercial": self.nombre_comercial,
            "nombre_rep_legal": self.nombre_rep_legal,
            "email":            self.email,
            "telefono":         self.telefono,
            "direccion":        self.direccion,
            "ambiente_sri":     self.ambiente_sri.value,
            "estado":           self.estado.value,
            "plan":             self.plan,
            "created_at":       self.created_at.isoformat(),
            "updated_at":       self.updated_at.isoformat(),
            "created_by":       self.created_by,
            "version":          self.version,
        }
