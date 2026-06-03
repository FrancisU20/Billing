"""
FrontendStack — despliega en us-east-1 (obligatorio para CloudFront).

Arquitectura:
  Usuario → CloudFront (edge GRU/São Paulo) → S3 (us-east-1, solo origen de CDN)
  CloudFront Function: reescritura SPA (no parche 404, rewrite real en el edge)
  ACM cert wildcard *.codelabsecuador.com desde CertificateStack (us-east-1)
  Route 53: billing-{env}.codelabsecuador.com → CloudFront

Nota: S3 en us-east-1 es correcto aquí — es el origen del CDN, no almacena
datos del negocio. Los usuarios se sirven desde el edge GRU (~5ms en Ecuador).
Los datos del negocio (Aurora, SQS, documentos) permanecen en sa-east-1.
"""
from aws_cdk import (
    Stack, RemovalPolicy, CfnOutput,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_route53 as route53,
    aws_route53_targets as targets,
)
from aws_cdk.aws_certificatemanager import ICertificate
from constructs import Construct

# CloudFront Function — reescritura SPA en el edge
# Reescribe todas las rutas sin extensión de archivo a /index.html
# Los assets estáticos (*.js, *.css, *.png, etc.) pasan directamente
_SPA_ROUTER_FUNCTION = """\
function handler(event) {
    var request = event.request;
    var uri = request.uri;

    // Pasar directamente si tiene extensión de archivo (assets estáticos de Next.js)
    if (uri.match(/\\.[a-zA-Z0-9]+$/)) {
        return request;
    }

    // Reescribir todas las rutas SPA a index.html para que React Router tome el control
    request.uri = '/index.html';
    return request;
}
"""


class FrontendStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: dict,
        certificate: ICertificate,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]
        domain_cfg = config["domain"]
        frontend_domain = domain_cfg["frontend"]
        hosted_zone_name = domain_cfg["hosted_zone"]
        hosted_zone_id = domain_cfg["hosted_zone_id"]

        removal = RemovalPolicy.RETAIN if env == "prod" else RemovalPolicy.DESTROY

        # S3 bucket — origen del CDN, acceso SOLO via CloudFront OAC
        self.web_bucket = s3.Bucket(
            self, "WebBucket",
            bucket_name=f"codelabs-billing-{env}-web",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal,
            auto_delete_objects=env != "prod",
            enforce_ssl=True,
            versioned=False,
        )

        # CloudFront Function — reescritura SPA en el edge (no parche 404)
        spa_router = cloudfront.Function(
            self, "SpaRouterFunction",
            function_name=f"codelabs-billing-{env}-spa-router",
            code=cloudfront.FunctionCode.from_inline(_SPA_ROUTER_FUNCTION),
            runtime=cloudfront.FunctionRuntime.JS_2_0,
            comment="Reescribe rutas SPA a index.html en el edge",
        )

        # CloudFront Distribution con OAC (Origin Access Control — más seguro que OAI)
        self.distribution = cloudfront.Distribution(
            self, "WebDistribution",
            comment=f"CodeLabs Billing Cloud - {env}",
            domain_names=[frontend_domain],
            certificate=certificate,
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.web_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
                function_associations=[
                    cloudfront.FunctionAssociation(
                        event_type=cloudfront.FunctionEventType.VIEWER_REQUEST,
                        function=spa_router,
                    )
                ],
            ),
            # Assets de Next.js con hash en nombre — cache agresiva
            additional_behaviors={
                "/_next/static/*": cloudfront.BehaviorOptions(
                    origin=origins.S3BucketOrigin.with_origin_access_control(self.web_bucket),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    compress=True,
                ),
            },
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            http_version=cloudfront.HttpVersion.HTTP2_AND_3,
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
        )

        # Route 53 — alias record
        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self, "HostedZone",
            hosted_zone_id=hosted_zone_id,
            zone_name=hosted_zone_name,
        )

        route53.ARecord(
            self, "FrontendAliasRecord",
            zone=hosted_zone,
            record_name=frontend_domain,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.distribution)
            ),
        )

        # Outputs — usados en CI/CD para deployar el frontend sin hardcodear valores
        CfnOutput(self, "WebBucketName",
                  value=self.web_bucket.bucket_name,
                  export_name=f"CodeLabsBilling-{env}-WebBucketName")

        CfnOutput(self, "CloudFrontDistributionId",
                  value=self.distribution.distribution_id,
                  export_name=f"CodeLabsBilling-{env}-CloudFrontDistId")

        CfnOutput(self, "FrontendUrl",
                  value=f"https://{frontend_domain}",
                  export_name=f"CodeLabsBilling-{env}-FrontendUrl")
