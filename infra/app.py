#!/usr/bin/env python3
import os
import yaml
import aws_cdk as cdk
from stacks.network_stack import NetworkStack
from stacks.auth_stack import AuthStack
from stacks.database_stack import DatabaseStack
from stacks.storage_stack import StorageStack
from stacks.queues_stack import QueuesStack
from stacks.api_stack import ApiStack
from stacks.security_stack import SecurityStack
from stacks.observability_stack import ObservabilityStack
from stacks.frontend_stack import FrontendStack
from stacks.certificate_stack import CertificateStack


def load_config(env: str) -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "config", f"{env}.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


app = cdk.App()

env_name = app.node.try_get_context("env") or "dev"
config = load_config(env_name)

account = os.environ.get("CDK_DEFAULT_ACCOUNT")

# Región principal — sa-east-1 (São Paulo)
sa_env = cdk.Environment(account=account, region=config["region"])

# us-east-1 — SOLO para CloudFront (certificado y distribución, requisito AWS)
useast1_env = cdk.Environment(account=account, region="us-east-1")

prefix = f"CodeLabsBilling-{env_name.capitalize()}"

# ── Infraestructura principal en sa-east-1 ────────────────────────────────────
network = NetworkStack(app, f"{prefix}-Network", config=config, env=sa_env)
auth = AuthStack(app, f"{prefix}-Auth", config=config, env=sa_env)
database = DatabaseStack(
    app, f"{prefix}-Database",
    config=config,
    vpc=network.vpc,
    env=sa_env,
)
storage = StorageStack(app, f"{prefix}-Storage", config=config, env=sa_env)
queues = QueuesStack(app, f"{prefix}-Queues", config=config, env=sa_env)
security = SecurityStack(app, f"{prefix}-Security", config=config, env=sa_env)
api = ApiStack(
    app, f"{prefix}-Api",
    config=config,
    vpc=network.vpc,
    database=database,
    storage=storage,
    queues=queues,
    auth=auth,
    api_cert=security.api_cert,
    env=sa_env,
)
observability = ObservabilityStack(
    app, f"{prefix}-Observability",
    config=config,
    api_stack=api,
    queues=queues,
    env=sa_env,
)

# ── Infraestructura CloudFront en us-east-1 ───────────────────────────────────
# CertificateStack y FrontendStack deben estar en us-east-1 (requisito AWS para CloudFront)
certificate = CertificateStack(app, f"{prefix}-Certificate", config=config, env=useast1_env)
frontend = FrontendStack(
    app, f"{prefix}-Frontend",
    config=config,
    certificate=certificate.wildcard_cert,
    env=useast1_env,
)
frontend.add_dependency(certificate)

# ── Dependencias explícitas sa-east-1 ─────────────────────────────────────────
database.add_dependency(network)
api.add_dependency(database)
api.add_dependency(auth)
api.add_dependency(storage)
api.add_dependency(queues)
api.add_dependency(security)
observability.add_dependency(api)

cdk.Tags.of(app).add("Project", "CodeLabsBillingCloud")
cdk.Tags.of(app).add("Environment", env_name)
cdk.Tags.of(app).add("ManagedBy", "CDK")

app.synth()
