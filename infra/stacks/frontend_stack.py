"""
FrontendStack — S3 + CloudFront + Route53 para el frontend Expo web.

Arquitectura:

  Browser → billing-{env}.codelabsecuador.com
              CloudFront distribution (us-east-1 edge)
                behavior /api/*  → api-billing-{env}.codelabsecuador.com
                                   (CloudFront Function elimina el prefijo /api)
                behavior default → S3 bucket privado via OAC
              Route53 A + AAAA  → alias CloudFront

Routing SPA:
  S3 devuelve 403 para rutas que no existen como objetos (porque el bucket es
  privado y OAC intercepta). CloudFront mapea 403/404 → index.html con status
  200 para que Expo Router maneje todas las rutas en cliente.

Cache strategy:
  Política personalizada con default TTL = 0, max TTL = 1 año.
  CloudFront respeta el header Cache-Control del objeto S3:
    - index.html / *.json  → no-cache,no-store  (CI sube sin TTL)
    - _expo/**/*.js,.css   → immutable,max-age=31536000 (hash en el nombre)
  Esto evita servir versiones viejas del entry point y maximiza el cache hit
  de los assets con fingerprint.

Routing /api/*:
  CloudFront reenvía las llamadas a la API al mismo dominio que el frontend.
  Una CloudFront Function (viewer-request) quita el prefijo /api antes de
  reenviar a API Gateway, de modo que /api/tenants → /tenants.
  El frontend puede usar EXPO_PUBLIC_API_URL="" (mismo origen) o el dominio
  directo — ambos funcionan; el comportamiento es transparente.
"""
from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_s3 as s3,
)
from constructs import Construct


class FrontendStack(Stack):
    def __init__(
        self,
        scope:        Construct,
        construct_id: str,
        config:       dict,
        certificate,          # CertificateStack — expone .certificate (us-east-1)
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env            = config["env"]
        domain_cfg     = config.get("domain", {})
        hz_name        = domain_cfg.get("hosted_zone", "")
        frontend_domain = domain_cfg.get("frontend", "")
        api_domain     = domain_cfg.get("api", "")
        is_prod        = env == "prod"
        removal        = RemovalPolicy.RETAIN if is_prod else RemovalPolicy.DESTROY

        # ── S3 Bucket — privado, acceso exclusivo via OAC ─────────────────────
        # Nombre determinista → el workflow de CI lo usa sin necesitar un Secret.
        # enforce_ssl garantiza que solo se aceptan conexiones HTTPS al bucket.
        self.bucket = s3.Bucket(
            self, "FrontendBucket",
            bucket_name          = f"codelabs-billing-{env}-frontend",
            block_public_access  = s3.BlockPublicAccess.BLOCK_ALL,
            encryption           = s3.BucketEncryption.S3_MANAGED,
            versioned            = is_prod,
            removal_policy       = removal,
            auto_delete_objects  = not is_prod,
            enforce_ssl          = True,
        )

        # ── Cache policy — respeta Cache-Control del objeto S3 ────────────────
        # min=0, default=0, max=365d.
        # Con default=0, CloudFront reenvía sin TTL propio y deja que el
        # header Cache-Control del objeto en S3 dicte el comportamiento del
        # browser. Assets con hash (immutable) quedan en edge hasta max_ttl.
        spa_cache_policy = cloudfront.CachePolicy(
            self, "SpaCachePolicy",
            cache_policy_name        = f"codelabs-billing-{env}-spa",
            default_ttl              = Duration.seconds(0),
            min_ttl                  = Duration.seconds(0),
            max_ttl                  = Duration.days(365),
            enable_accept_encoding_gzip    = True,
            enable_accept_encoding_brotli  = True,
        )

        # ── SPA error responses ───────────────────────────────────────────────
        # S3 + OAC devuelve 403 (no 404) cuando el objeto no existe porque el
        # bucket es privado. Mapeamos ambos códigos a index.html para que Expo
        # Router los resuelva en cliente. TTL = 0 para que los cambios de rutas
        # lleguen al usuario inmediatamente después de un deploy.
        error_responses = [
            cloudfront.ErrorResponse(
                http_status           = 403,
                response_http_status  = 200,
                response_page_path    = "/index.html",
                ttl                   = Duration.seconds(0),
            ),
            cloudfront.ErrorResponse(
                http_status           = 404,
                response_http_status  = 200,
                response_page_path    = "/index.html",
                ttl                   = Duration.seconds(0),
            ),
        ]

        # ── Distribución CloudFront ───────────────────────────────────────────
        # PRICE_CLASS_ALL incluye edge locations en Sudamérica (São Paulo,
        # Bogotá, Buenos Aires), crítico para latencia de usuarios ecuatorianos.
        self.distribution = cloudfront.Distribution(
            self, "FrontendDistribution",
            comment              = f"codelabs-billing-{env} frontend",
            domain_names         = [frontend_domain],
            certificate          = certificate.certificate,
            price_class          = cloudfront.PriceClass.PRICE_CLASS_ALL,
            default_root_object  = "index.html",
            error_responses      = error_responses,
            default_behavior     = cloudfront.BehaviorOptions(
                origin                 = origins.S3BucketOrigin.with_origin_access_control(
                    self.bucket
                ),
                viewer_protocol_policy = cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy           = spa_cache_policy,
                compress               = True,
            ),
        )

        # ── Behavior /api/* → API Gateway ─────────────────────────────────────
        # Proxy transparente: el frontend puede llamar /api/tenants en lugar de
        # https://api-billing-{env}.codelabsecuador.com/tenants.
        # La CloudFront Function quita el prefijo /api antes de reenviar, de
        # modo que /api/tenants llega a API Gateway como /tenants.
        # CACHING_DISABLED + ALL_VIEWER_EXCEPT_HOST_HEADER garantiza que los
        # headers de auth (Authorization, X-Idempotency-Key) y el body se
        # reenvíen correctamente sin que CloudFront cachee las respuestas.
        if api_domain:
            strip_api_prefix = cloudfront.Function(
                self, "StripApiPrefixFn",
                function_name = f"codelabs-billing-{env}-strip-api-prefix",
                code          = cloudfront.FunctionCode.from_inline(
                    # slice(4) elimina los primeros 4 chars ("/api") del path.
                    # El path pattern /api/* garantiza que el URI siempre
                    # empieza con "/api/" — el resultado nunca es vacío.
                    "function handler(event){"
                    "var r=event.request;"
                    "r.uri=r.uri.slice(4)||'/';"
                    "return r;}"
                ),
                runtime = cloudfront.FunctionRuntime.JS_2_0,
            )

            self.distribution.add_behavior(
                path_pattern           = "/api/*",
                origin                 = origins.HttpOrigin(
                    api_domain,
                    protocol_policy = cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                ),
                viewer_protocol_policy = cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                allowed_methods        = cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy           = cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy  = (
                    cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER
                ),
                function_associations  = [
                    cloudfront.FunctionAssociation(
                        function   = strip_api_prefix,
                        event_type = cloudfront.FunctionEventType.VIEWER_REQUEST,
                    )
                ],
            )

        # ── Route53 — A + AAAA (IPv4 e IPv6) alias a CloudFront ──────────────
        if hz_name and frontend_domain:
            hosted_zone = route53.HostedZone.from_lookup(
                self, "HostedZone",
                domain_name=hz_name,
            )
            cf_target = route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.distribution)
            )
            route53.ARecord(
                self, "FrontendARecord",
                zone        = hosted_zone,
                record_name = frontend_domain,
                target      = cf_target,
            )
            route53.AaaaRecord(
                self, "FrontendAaaaRecord",
                zone        = hosted_zone,
                record_name = frontend_domain,
                target      = cf_target,
            )

        # ── Outputs ───────────────────────────────────────────────────────────
        # FrontendBucketName y FrontendDistributionId son leídos por el
        # workflow de CI directamente desde CloudFormation — no hacen falta
        # como GitHub Secrets.
        CfnOutput(
            self, "FrontendBucketName",
            value       = self.bucket.bucket_name,
            export_name = f"CodeLabsBilling-{env}-FrontendBucketName",
        )
        CfnOutput(
            self, "FrontendDistributionId",
            value       = self.distribution.distribution_id,
            export_name = f"CodeLabsBilling-{env}-FrontendDistributionId",
        )
        CfnOutput(
            self, "FrontendUrl",
            value       = f"https://{frontend_domain}",
            export_name = f"CodeLabsBilling-{env}-FrontendUrl",
        )
