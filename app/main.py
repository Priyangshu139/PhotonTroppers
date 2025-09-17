import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import predict_routes, train_routes, data_routes, getdata_routes, picron_routes, telegram_routes, telegram_notify_routes, shell_routes



# Create FastAPI app with production settings
app = FastAPI(
    title="PhotonTroppers API",
    description="Medicine Quality Analysis using Sensor Data and Machine Learning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for web frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Health check endpoint for Render
@app.get("/")
async def root():
    return {
        "message": "PhotonTroppers API is running",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include routers
app.include_router(predict_routes.router, prefix="/predict", tags=["Predict"])
app.include_router(train_routes.router, prefix="/train", tags=["Train"])
app.include_router(data_routes.router, prefix="/data", tags=["Data"])
app.include_router(getdata_routes.router, prefix="/getdata", tags=["GetData"])
app.include_router(picron_routes.router, prefix="/picron", tags=["Picron"])
app.include_router(telegram_routes.router, prefix="/telegram", tags=["Telegram"])
app.include_router(telegram_notify_routes.router, tags=["TelegramNotify"])
app.include_router(shell_routes.router, prefix="/shell", tags=["Shell"])




# Create models directory on startup
@app.on_event("startup")
async def startup_event():
    os.makedirs("app/models", exist_ok=True)
    print("PhotonTroppers API started successfully")

# Graceful shutdown
@app.on_event("shutdown")
async def shutdown_event():
    print("PhotonTroppers API shutting down") 