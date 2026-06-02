from aws_cdk import Stack, RemovalPolicy, aws_kms as kms, aws_wafv2 as waf
from constructs import Construct


class SecurityStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]

        # KMS key maestra para Secrets Manager
        self.secrets_key = kms.Key(
            self, "SecretsKey",
            alias=f"codelabs-billing-{env}-secrets",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN if env == "prod" else RemovalPolicy.DESTROY,
        )

        # WAF — solo si está habilitado en config (producción)
        self.web_acl = None
        if config["waf"]["enabled"]:
            self.web_acl = waf.CfnWebACL(
                self, "WebAcl",
                name=f"codelabs-billing-{env}-waf",
                scope="REGIONAL",  # para API Gateway; usar CLOUDFRONT para CloudFront
                default_action=waf.CfnWebACL.DefaultActionProperty(allow={}),
                visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                    cloud_watch_metrics_enabled=True,
                    metric_name=f"codelabs-billing-{env}-waf",
                    sampled_requests_enabled=True,
                ),
                rules=[
                    # AWS managed rules — OWASP básico
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
                    # Rate limiting por IP — 1000 req / 5 minutos
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
