from aws_cdk import Stack, RemovalPolicy, Duration, CfnOutput, aws_cognito as cognito
from constructs import Construct


class AuthStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]
        mfa = config["cognito"]["mfa_enforcement"]

        self.user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name=f"codelabs-billing-{env}",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            mfa=cognito.Mfa[mfa],
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.RETAIN if env == "prod" else RemovalPolicy.DESTROY,
            custom_attributes={
                "tenant_id": cognito.StringAttribute(mutable=True),
                "role": cognito.StringAttribute(mutable=True),
                "is_superadmin": cognito.BooleanAttribute(mutable=True),
            },
        )

        self.web_client = self.user_pool.add_client(
            "WebClient",
            user_pool_client_name=f"codelabs-billing-{env}-web",
            auth_flows=cognito.AuthFlow(user_srp=True, user_password=False),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE],
            ),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            prevent_user_existence_errors=True,
        )

        self.api_client = self.user_pool.add_client(
            "ApiClient",
            user_pool_client_name=f"codelabs-billing-{env}-api",
            auth_flows=cognito.AuthFlow(user_srp=True),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(1),
            prevent_user_existence_errors=True,
        )

        self.mobile_client = self.user_pool.add_client(
            "MobileClient",
            user_pool_client_name=f"codelabs-billing-{env}-mobile",
            auth_flows=cognito.AuthFlow(user_srp=True),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE],
            ),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            prevent_user_existence_errors=True,
        )

        # Outputs para CI/CD — leídos dinámicamente en el workflow de deploy
        # Evita hardcodear IDs de Cognito en el código del repositorio
        CfnOutput(self, "UserPoolId",
                  value=self.user_pool.user_pool_id,
                  export_name=f"CodeLabsBilling-{env}-UserPoolId")

        CfnOutput(self, "WebClientId",
                  value=self.web_client.user_pool_client_id,
                  export_name=f"CodeLabsBilling-{env}-WebClientId")
