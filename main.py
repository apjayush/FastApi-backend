from fastapi import FastAPI
from app.routers import webhook
from app.routers import slots

app = FastAPI()

# include webhook route
app.include_router(webhook.router)
app.include_router(slots.router)