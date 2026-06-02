from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

_bearer = HTTPBearer(auto_error=False)


async def get_tenant_context(request: Request) -> dict:
    """
    Extrae tenant_id y rol desde el JWT de Cognito o desde un API Key.
    Inyecta el contexto en request.state para que los use cases lo consuman.
    El tenant_id NUNCA viene del body — siempre del token autenticado.
    """
    # JWT de Cognito (web/mobile)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ")
        try:
            # Decodificar sin verificar firma aquí (API Gateway/Lambda Authorizer ya verificó)
            # En el Lambda Authorizer real se valida la firma con las JWKS de Cognito
            claims = jwt.decode(token, options={"verify_signature": False})
            return {
                "tenant_id": claims.get("custom:tenant_id"),
                "user_id": claims.get("sub"),
                "role": claims.get("custom:role", "viewer"),
                "is_superadmin": claims.get("custom:is_superadmin", False),
            }
        except Exception:
            raise HTTPException(status_code=401, detail="Token inválido")

    # API Key (integraciones externas)
    api_key = request.headers.get("X-Api-Key")
    if api_key:
        # La resolución del tenant por API Key ocurre en el use case con DB lookup
        return {"api_key": api_key, "tenant_id": None, "role": "api"}

    raise HTTPException(status_code=401, detail="Autenticación requerida")
