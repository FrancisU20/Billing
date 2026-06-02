from mangum import Mangum

from app.main import app

# Mangum adapta ASGI (FastAPI) al formato de eventos de AWS Lambda + API Gateway
handler = Mangum(app, lifespan="off")
