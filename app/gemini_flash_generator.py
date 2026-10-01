"""Nutrition / recovery tips (uses the fast 'flash' Gemini model)."""
from . import config
from .gemini_client import generate_text


def generate_nutrition_tip_with_flash(goal: str) -> str:
    prompt = f"""Give ONE concise, practical nutrition or recovery tip (2-3 sentences maximum)
for someone whose fitness goal is "{goal}".
Use plain text only, no markdown, no lists, no greeting."""
    return generate_text(config.GEMINI_FLASH_MODEL, prompt)