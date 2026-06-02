from aws_cdk import (
    Stack, RemovalPolicy,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_kms as kms,
)
from constructs import Construct


class FrontendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]
        domain_cfg = config["domain"]

        if not domain_cfg["enabled"]:
            # En dev no se despliega CloudFront — el frontend corre local con next dev
            return

        removal = RemovalPolicy.RETAIN if env == "prod" else RemovalPolicy.DESTROY

        web_bucket = s3.Bucket(
            self, "WebBucket",
            bucket_name=f"codelabs-billing-{env}-web",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal,
            auto_delete_objects=env != "prod",
            enforce_ssl=True,
        )

        distribution = cloudfront.Distribution(
            self, "WebDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(web_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",  # SPA fallback
                ),
            ],
        )
