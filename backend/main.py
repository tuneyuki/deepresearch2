from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers.research import router as research_router

app = FastAPI(title="Deep Research API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
