from fastapi import FastAPI
from app.db.database import Base, engine
from app.routers import auth, user, database_connection, query, admin

# Ensure models are loaded so SQL Alchemy registers metadata
from app import models

app = FastAPI(
    title="AI-Powered SQL Generator & Executor API",
    description="Translate Natural Language to SQL and execute against databases securely using LLMs.",
    version="1.0.0"
)

# Register routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(database_connection.router)
app.include_router(query.router)
app.include_router(admin.router)


@app.on_event("startup")
async def startup_db_init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AI-Powered SQL API",
        "documentation": "/docs"
    }
