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


def load_config(env: str) -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "config", f"{env}.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


app = cdk.App()

env_name = app.node.try_get_context("env") or "dev"
config = load_config(env_name)

aws_env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=config["region"],
)

prefix = f"CodeLabsBilling-{env_name.capitalize()}"

network = NetworkStack(app, f"{prefix}-Network", config=config, env=aws_env)
auth = AuthStack(app, f"{prefix}-Auth", config=config, env=aws_env)
database = DatabaseStack(
    app, f"{prefix}-Database",
    config=config,
    vpc=network.vpc,
    env=aws_env,
)
storage = StorageStack(app, f"{prefix}-Storage", config=config, env=aws_env)
queues = QueuesStack(app, f"{prefix}-Queues", config=config, env=aws_env)
security = SecurityStack(app, f"{prefix}-Security", config=config, env=aws_env)
api = ApiStack(
    app, f"{prefix}-Api",
    config=config,
    vpc=network.vpc,
    database=database,
    storage=storage,
    queues=queues,
    auth=auth,
    env=aws_env,
)
observability = ObservabilityStack(
    app, f"{prefix}-Observability",
    config=config,
    api_stack=api,
    queues=queues,
    env=aws_env,
)
frontend = FrontendStack(app, f"{prefix}-Frontend", config=config, env=aws_env)

# Dependencias explícitas
database.add_dependency(network)
api.add_dependency(database)
api.add_dependency(auth)
api.add_dependency(storage)
api.add_dependency(queues)
observability.add_dependency(api)

cdk.Tags.of(app).add("Project", "CodeLabsBillingCloud")
cdk.Tags.of(app).add("Environment", env_name)
cdk.Tags.of(app).add("ManagedBy", "CDK")

app.synth()
