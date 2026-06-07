"""
AuthStack — Amazon Cognito User Pool.

Un solo User Pool para todos los usuarios del sistema:
  superadmin  → gestiona la plataforma (Francisco)
  owner       → dueño/representante legal del tenant
  admin       → contador, acceso operativo completo
  viewer      → solo lectura

Claims en el JWT (ID Token):
  custom:tenant_id     UUID del tenant (vacío para superadmin)
  custom:role          superadmin | owner | admin | viewer
  custom:is_superadmin true | false

El frontend y los Lambdas usan el ID Token como Bearer token
porque contiene los custom attributes. El HTTP API Gateway
JWT authorizer valida firma y expiración automáticamente.

Self-signup deshabilitado — todos los usuarios son creados
por admin (superadmin crea owners, owners crean admins/viewers).
"""
from aws_cdk import (
    Stack, Duration, RemovalPolicy, CfnOutput,
    aws_cognito as cognito,
)
from constructs import Construct


class AuthStack(Stack):
    def __init__(
        self,
        scope:        Construct,
        construct_id: str,
        config:       dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env      = config["env"]
        cognito_cfg = config.get("cognito", {})
        removal  = RemovalPolicy.RETAIN if env == "prod" else RemovalPolicy.DESTROY

        # ── User Pool ─────────────────────────────────────────────────────────
        self.user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name       = f"codelabs-billing-{env}",
            self_sign_up_enabled = False,
            sign_in_aliases      = cognito.SignInAliases(email=True),
            auto_verify          = cognito.AutoVerifiedAttrs(email=True),
            account_recovery     = cognito.AccountRecovery.EMAIL_ONLY,
            mfa                  = cognito.Mfa[cognito_cfg.get("mfa", "OFF")],
            password_policy      = cognito.PasswordPolicy(
                min_length        = 12,
                require_lowercase = True,
                require_uppercase = True,
                require_digits    = True,
                require_symbols   = True,
            ),
            # Atributos personalizados — mutable para que el Lambda los pueda actualizar
            custom_attributes    = {
                "tenant_id":    cognito.StringAttribute(mutable=True),
                "role":         cognito.StringAttribute(mutable=True),
                "is_superadmin":cognito.BooleanAttribute(mutable=True),
            },
            removal_policy = removal,
        )

        # ── Web Client (frontend web + mobile Expo) ───────────────────────────
        # Sin client_secret: cliente público (SPA / app móvil)
        # USER_SRP_AUTH: la contraseña nunca viaja en texto plano
        client_read_attrs = (
            cognito.ClientAttributes()
            .with_standard_attributes(email=True, email_verified=True)
            .with_custom_attributes("tenant_id", "role", "is_superadmin")
        )

        self.web_client = self.user_pool.add_client(
            "WebClient",
            user_pool_client_name = f"codelabs-billing-{env}-web",
            auth_flows            = cognito.AuthFlow(
                user_srp      = True,
                user_password = False,  # SRP only — más seguro
            ),
            read_attributes       = client_read_attrs,
            access_token_validity = Duration.hours(1),
            id_token_validity     = Duration.hours(1),
            refresh_token_validity= Duration.days(30),
            prevent_user_existence_errors = True,
            enable_token_revocation       = True,
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(self, "UserPoolId",
                  value       = self.user_pool.user_pool_id,
                  export_name = f"CodeLabsBilling-{env}-UserPoolId")

        CfnOutput(self, "UserPoolArn",
                  value       = self.user_pool.user_pool_arn,
                  export_name = f"CodeLabsBilling-{env}-UserPoolArn")

        CfnOutput(self, "WebClientId",
                  value       = self.web_client.user_pool_client_id,
                  export_name = f"CodeLabsBilling-{env}-WebClientId")
