"""FitBuddy application entry point.  Run:  uvicorn app.main:app --reload"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .database import init_db
from .routes import router

STATIC_DIR = os.path.join(config.BASE_DIR, "static")
os.makedirs(os.path.join(STATIC_DIR, "images"), exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()  # creates SQLite tables on startup
    yield


app = FastAPI(
    title="FitBuddy - AI Fitness Plan Generator",
    description="Personalized 7-day workout plans and nutrition tips powered by Google Gemini.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(router)