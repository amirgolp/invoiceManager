from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config.settings import settings
from app.routers import auth_router, workspace_router # ADDED workspace_router here
from app.db.database import connect_to_mongo, close_mongo_connection
from app.db.redis_db import get_redis_client, close_redis_connection
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Connecting to MongoDB...")
    connect_to_mongo()
    print("Connecting to Redis...")
    get_redis_client()
    yield
    # Shutdown
    print("Disconnecting from Redis...")
    close_redis_connection()
    print("Disconnecting from MongoDB...")
    close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    lifespan=lifespan
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router.router)
app.include_router(workspace_router.router) # ADDED workspace_router include here

@app.get("/")
async def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}"}
