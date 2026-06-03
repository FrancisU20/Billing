from aws_cdk import (
    Stack, RemovalPolicy, CfnOutput,
    aws_kms as kms,
    aws_wafv2 as waf,
    aws_certificatemanager as acm,
    aws_route53 as route53,
)
from constructs import Construct


class SecurityStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]
        domain_cfg = config["domain"]

        # KMS key maestra para Secrets Manager
        self.secrets_key = kms.Key(
            self, "SecretsKey",
            alias=f"codelabs-billing-{env}-secrets",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN if env == "prod" else RemovalPolicy.DESTROY,
        )

        # Certificado wildcard *.codelabsecuador.com en sa-east-1
        # Necesario para el custom domain de API Gateway (distinto al cert de CloudFront en us-east-1)
        # La validación DNS usa la misma zona hosteada → mismo CNAME → funciona en ambas regiones
        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self, "HostedZone",
            hosted_zone_id=domain_cfg["hosted_zone_id"],
            zone_name=domain_cfg["hosted_zone"],
        )

        self.api_cert = acm.Certificate(
            self, "ApiWildcardCert",
            domain_name=f"*.{domain_cfg['hosted_zone']}",
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )

        CfnOutput(self, "ApiWildcardCertArn",
                  value=self.api_cert.certificate_arn,
                  export_name=f"CodeLabsBilling-{env}-ApiWildcardCertArn-saeast1")

        # WAF — solo en producción
        self.web_acl = None
        if config["waf"]["enabled"]:
            self.web_acl = waf.CfnWebACL(
                self, "WebAcl",
                name=f"codelabs-billing-{env}-waf",
                scope="REGIONAL",
                default_action=waf.CfnWebACL.DefaultActionProperty(allow={}),
                visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                    cloud_watch_metrics_enabled=True,
                    metric_name=f"codelabs-billing-{env}-waf",
                    sampled_requests_enabled=True,
                ),
                rules=[
                    waf.CfnWebACL.RuleProperty(
                        name="AWSManagedRulesCommonRuleSet",
                        priority=1,
                        override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
                        statement=waf.CfnWebACL.StatementProperty(
                            managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                                vendor_name="AWS",
                                name="AWSManagedRulesCommonRuleSet",
                            )
                        ),
                        visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                            cloud_watch_metrics_enabled=True,
                            metric_name="CommonRuleSet",
                            sampled_requests_enabled=True,
                        ),
                    ),
                    waf.CfnWebACL.RuleProperty(
                        name="RateLimitByIp",
                        priority=2,
                        action=waf.CfnWebACL.RuleActionProperty(block={}),
                        statement=waf.CfnWebACL.StatementProperty(
                            rate_based_statement=waf.CfnWebACL.RateBasedStatementProperty(
                                limit=1000,
                                aggregate_key_type="IP",
                            )
                        ),
                        visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                            cloud_watch_metrics_enabled=True,
                            metric_name="RateLimitByIp",
                            sampled_requests_enabled=True,
                        ),
                    ),
                ],
            )
