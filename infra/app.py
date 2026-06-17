#!/usr/bin/env python3
"""
CDK App — CodeLabs Billing Cloud.

Reglas:
- Solo dev por ahora. Prod no se toca hasta tener clientes.
- Un stack por dominio funcional — sin archivos god.
- Despliegue: make deploy  (perfil codelabs, sa-east-1)

Stacks:
  CodeLabsBilling-Dev-Database    → DynamoDB tables
  CodeLabsBilling-Dev-Auth        → Cognito User Pool
  CodeLabsBilling-Dev-Queues      → SQS queues
  CodeLabsBilling-Dev-Api         → Lambda functions + HTTP API Gateway
  CodeLabsBilling-Dev-Certificate → ACM cert CloudFront (us-east-1)
  CodeLabsBilling-Dev-Frontend    → S3 + CloudFront + Route53 (sa-east-1)

Nota cross-region:
  CloudFront requiere que el certificado esté en us-east-1. CertificateStack
  se despliega allí y FrontendStack lo consume via cross_region_references.
  CDK usa SSM Parameter Store para pasar el ARN del cert entre regiones
  sin ningún acoplamiento manual.
"""
import os

import aws_cdk as cdk
import yaml

from stacks.api_stack         import ApiStack
from stacks.auth_stack        import AuthStack
from stacks.certificate_stack import CertificateStack
from stacks.database_stack    import DatabaseStack
from stacks.frontend_stack    import FrontendStack
from stacks.queues_stack      import QueuesStack


def load_config(env: str) -> dict:
    path = os.path.join(os.path.dirname(__file__), "config", f"{env}.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


app      = cdk.App()
env_name = app.node.try_get_context("env") or "dev"
config   = load_config(env_name)
account  = os.environ.get("CDK_DEFAULT_ACCOUNT")
sa_env   = cdk.Environment(account=account, region=config["region"])
us_env   = cdk.Environment(account=account, region="us-east-1")
prefix   = f"CodeLabsBilling-{env_name.capitalize()}"

database    = DatabaseStack(app, f"{prefix}-Database", config=config, env=sa_env)
auth        = AuthStack(app,     f"{prefix}-Auth",     config=config, env=sa_env)
queues      = QueuesStack(app,   f"{prefix}-Queues",   config=config, env=sa_env)
api         = ApiStack(app,      f"{prefix}-Api",      config=config, env=sa_env,
                       database=database, auth=auth, queues=queues)
certificate = CertificateStack(app, f"{prefix}-Certificate", config=config,
                               env=us_env, cross_region_references=True)
frontend    = FrontendStack(app, f"{prefix}-Frontend", config=config,
                            env=sa_env, certificate=certificate,
                            cross_region_references=True)

cdk.Tags.of(app).add("Project",     "CodeLabsBillingCloud")
cdk.Tags.of(app).add("Environment", env_name)
cdk.Tags.of(app).add("ManagedBy",   "CDK")

app.synth()
