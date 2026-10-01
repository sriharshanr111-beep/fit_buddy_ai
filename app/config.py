"""Central configuration: reads values from the environment / .env file."""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# API key (either variable name works)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""

# Models
GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-3.8-flash")
GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-3.5-flash-lite")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'fitbuddy.db')}")

# Allowed form values
GOALS = ["weight loss", "muscle gain", "general wellness", "flexibility", "endurance"]
INTENSITIES = ["low", "medium", "high"]