from fastapi import FastAPI
from app.routers import data_routes

app = FastAPI(title="Factory AI API")

app.include_router(data_routes.router)
