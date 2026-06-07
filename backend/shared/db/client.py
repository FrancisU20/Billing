"""
Cliente DynamoDB — singleton inicializado en cold start.

Usa siempre el endpoint regional de AWS resuelto por boto3 con las credenciales
del ambiente actual. En local se trabaja contra las tablas dev reales.

Uso:
    from shared.db.client import get_table
    _table = get_table("TENANTS_TABLE")   # fuera del handler
"""
import os

import boto3
from boto3.dynamodb.table import TableResource

_dynamodb = boto3.resource("dynamodb")
_tables: dict[str, TableResource] = {}


def get_table(env_var: str) -> TableResource:
    """Retorna el Table correspondiente al env_var. Singleton por tabla."""
    if env_var not in _tables:
        table_name = os.environ.get(env_var, "")
        if not table_name:
            raise RuntimeError(f"Env var '{env_var}' no configurada")
        _tables[env_var] = _dynamodb.Table(table_name)
    return _tables[env_var]
