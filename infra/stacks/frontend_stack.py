from aws_cdk import (
    Stack, RemovalPolicy,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
)
from constructs import Construct


class FrontendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]
        domain_cfg = config["domain"]

        if not domain_cfg["enabled"]:
            # En dev no se despliega CloudFront — frontend corre local con next dev
            return

        frontend_domain = domain_cfg["frontend"]   # e.g. billing-staging.codelabsecuador.com
        hosted_zone_name = domain_cfg["hosted_zone"]  # codelabsecuador.com

        removal = RemovalPolicy.RETAIN if env == "prod" else RemovalPolicy.DESTROY

        # S3 bucket para los archivos estáticos del Next.js build
        web_bucket = s3.Bucket(
            self, "WebBucket",
            bucket_name=f"codelabs-billing-{env}-web",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal,
            auto_delete_objects=env != "prod",
            enforce_ssl=True,
        )

        # Certificado SSL — debe estar en us-east-1 para CloudFront (requisito de AWS)
        # ACM en us-east-1 aunque el resto del infra esté en sa-east-1
        certificate = acm.Certificate(
            self, "Certificate",
            domain_name=frontend_domain,
            validation=acm.CertificateValidation.from_dns(),
        )

        distribution = cloudfront.Distribution(
            self, "WebDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(web_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            domain_names=[frontend_domain],
            certificate=certificate,
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
            ],
        )

        # Registro DNS en Route 53
        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name=hosted_zone_name,
        )
        route53.ARecord(
            self, "FrontendAliasRecord",
            zone=hosted_zone,
            record_name=frontend_domain,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(distribution)
            ),
        )

        self.distribution = distribution
        self.web_bucket = web_bucket
