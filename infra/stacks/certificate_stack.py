"""
CertificateStack — despliega en us-east-1 (obligatorio para CloudFront).

Crea el certificado wildcard *.codelabsecuador.com validado via DNS con Route 53.
La validación es automática porque la zona hosteada está en la misma cuenta AWS.

Este stack SIEMPRE va a us-east-1, independientemente del ambiente.
El resto del infra va a sa-east-1.
"""
from aws_cdk import Stack, CfnOutput, aws_certificatemanager as acm, aws_route53 as route53
from constructs import Construct


class CertificateStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        domain_cfg = config["domain"]
        hosted_zone_name = domain_cfg["hosted_zone"]
        hosted_zone_id = domain_cfg["hosted_zone_id"]

        # Importar la zona hosteada existente (no la crea, solo la referencia)
        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self, "HostedZone",
            hosted_zone_id=hosted_zone_id,
            zone_name=hosted_zone_name,
        )

        # Wildcard cert para CloudFront — debe estar en us-east-1 (AWS constraint)
        # Cubre: billing-dev, billing, billing-staging, y cualquier subdominio futuro
        self.wildcard_cert = acm.Certificate(
            self, "WildcardCert",
            domain_name=f"*.{hosted_zone_name}",
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )

        CfnOutput(self, "WildcardCertArn",
                  value=self.wildcard_cert.certificate_arn,
                  export_name=f"CodeLabsBilling-{config['env']}-WildcardCertArn-useast1")
