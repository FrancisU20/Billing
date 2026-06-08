"""
CertificateStack — Certificado ACM para CloudFront.

CloudFront requiere que el certificado esté en us-east-1 (requisito global de AWS).
Este stack se despliega exclusivamente en us-east-1 y expone self.certificate
para que FrontendStack lo consuma a través de cross_region_references.

CDK escribe el ARN del certificado en un SSM Parameter en us-east-1 y lo lee
desde sa-east-1 durante el synth del FrontendStack. No hay acoplamiento directo
entre regiones en runtime.
"""
from aws_cdk import (
    CfnOutput,
    Stack,
    aws_certificatemanager as acm,
    aws_route53 as route53,
)
from constructs import Construct


class CertificateStack(Stack):
    def __init__(
        self,
        scope:        Construct,
        construct_id: str,
        config:       dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env           = config["env"]
        domain_cfg    = config.get("domain", {})
        hz_name       = domain_cfg.get("hosted_zone", "")
        frontend_domain = domain_cfg.get("frontend", "")

        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name=hz_name,
        )

        # Validación DNS automática — CDK escribe el registro CNAME en Route53.
        # El certificado tarda ~2 min en validarse la primera vez.
        self.certificate = acm.Certificate(
            self, "FrontendCertificate",
            domain_name=frontend_domain,
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )

        CfnOutput(
            self, "FrontendCertificateArn",
            value=self.certificate.certificate_arn,
            export_name=f"CodeLabsBilling-{env}-FrontendCertArn",
        )
