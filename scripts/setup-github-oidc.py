#!/usr/bin/env python3
"""
Crea el proveedor OIDC de GitHub y el rol IAM para GitHub Actions.
Ejecutar UNA SOLA VEZ con el perfil AWS codelabs, antes del CDK bootstrap.

Uso:
  python scripts/setup-github-oidc.py --env dev

Prerequisito: AWS CLI configurado con perfil 'codelabs'
  aws configure --profile codelabs
"""
import json
import sys
import argparse
import boto3
from botocore.exceptions import ClientError

GITHUB_REPO = "FrancisU20/CodeLabsBillingCloud"
OIDC_URL = "https://token.actions.githubusercontent.com"
# Thumbprint oficial de GitHub — válido y estático
OIDC_THUMBPRINT = "6938fd4d98bab03faadb97b34396831e3780aea1"


def main() -> None:
    parser = argparse.ArgumentParser(description="Setup GitHub OIDC role para CodeLabs Billing Cloud")
    parser.add_argument("--env", required=True, choices=["dev", "staging", "prod"], help="Ambiente")
    parser.add_argument("--profile", default="codelabs", help="Perfil AWS (default: codelabs)")
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile)
    iam = session.client("iam")
    sts = session.client("sts")

    account_id = sts.get_caller_identity()["Account"]
    role_name = f"CodeLabsBilling-GitHubActions-{args.env.capitalize()}"
    provider_arn = f"arn:aws:iam::{account_id}:oidc-provider/token.actions.githubusercontent.com"

    print(f"  Account: {account_id}")
    print(f"  Ambiente: {args.env}")
    print(f"  Rol: {role_name}")
    print()

    # 1. Crear OIDC provider (idempotente)
    try:
        iam.get_open_id_connect_provider(OpenIDConnectProviderArn=provider_arn)
        print(f"✓ OIDC provider ya existe")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            iam.create_open_id_connect_provider(
                Url=OIDC_URL,
                ClientIDList=["sts.amazonaws.com"],
                ThumbprintList=[OIDC_THUMBPRINT],
            )
            print(f"✓ OIDC provider creado")
        else:
            raise

    # 2. Trust policy — permite todos los branches/tags del repo
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Federated": provider_arn},
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    },
                    "StringLike": {
                        # Permite develop, main y cualquier tag v*
                        "token.actions.githubusercontent.com:sub": f"repo:{GITHUB_REPO}:*",
                    },
                },
            }
        ],
    }

    # 3. Crear o actualizar rol (idempotente)
    try:
        response = iam.get_role(RoleName=role_name)
        role_arn = response["Role"]["Arn"]
        # Actualizar trust policy si el rol ya existe
        iam.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=json.dumps(trust_policy),
        )
        print(f"✓ Rol ya existe — trust policy actualizada")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            response = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"GitHub Actions OIDC role - CodeLabs Billing Cloud ({args.env})",
                MaxSessionDuration=3600,
            )
            role_arn = response["Role"]["Arn"]
            print(f"✓ Rol creado: {role_arn}")
        else:
            raise

    # 4. Adjuntar AdministratorAccess (suficiente para CDK en dev)
    try:
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess",
        )
        print(f"✓ AdministratorAccess adjuntado al rol")
    except ClientError as e:
        if "already attached" in str(e).lower():
            print(f"✓ AdministratorAccess ya estaba adjuntado")
        else:
            raise

    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

    print()
    print("=" * 65)
    print("ROLE ARN — copiar en GitHub Secrets como AWS_OIDC_ROLE_ARN:")
    print()
    print(f"  {role_arn}")
    print()
    print("=" * 65)
    print()
    print("Próximos pasos:")
    print(f"  1. Ir a: https://github.com/{GITHUB_REPO}/settings/secrets/actions")
    print(f"  2. Crear secret: AWS_OIDC_ROLE_ARN = {role_arn}")
    print(f"  3. Ejecutar CDK bootstrap:")
    print(f"     make cdk-bootstrap")
    print(f"  4. Hacer push a develop para triggerear el deploy")
    print()


if __name__ == "__main__":
    main()
