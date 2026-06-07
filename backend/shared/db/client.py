"""
DynamoDB client — singleton initialized at cold start.

Always uses the regional AWS endpoint resolved by boto3 with the current
environment's credentials. Locally it works against the real dev tables.

Usage:
    from shared.db.client import get_table
    _table = get_table("TENANTS_TABLE")   # outside the handler
"""
import os

import boto3
from boto3.dynamodb.table import TableResource

_dynamodb = boto3.resource("dynamodb")
_tables: dict[str, TableResource] = {}


def get_table(env_var: str) -> TableResource:
    """Return the Table for the given env_var. Singleton per table."""
    if env_var not in _tables:
        table_name = os.environ.get(env_var, "")
        if not table_name:
            raise RuntimeError(f"Env var '{env_var}' not set")
        _tables[env_var] = _dynamodb.Table(table_name)
    return _tables[env_var]
