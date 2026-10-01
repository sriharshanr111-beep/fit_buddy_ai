"""Workout plan generation (uses the 'pro' Gemini model)."""
from . import config
from .gemini_client import generate_text


def generate_workout_gemini(username: str, age: int, weight: float, goal: str, intensity: str) -> str:
    prompt = f"""You are an experienced certified personal trainer.
Create a personalized 7-day workout plan for this person:

Name: {username}
Age: {age}
Weight: {weight} kg
Fitness goal: {goal}
Preferred intensity: {intensity}

Rules:
- Cover Day 1 to Day 7. Include rest/recovery days appropriate for the intensity.
- For EVERY day use exactly this layout:
  Day N - Focus
  Warm-up (5-10 mins): ...
  Main workout: exercise name - sets x reps (or duration) - rest interval
  Cooldown / recovery: ...
- Keep it safe and realistic for the person's age and intensity level.
- Use PLAIN TEXT only. Do not use markdown, asterisks, or tables.
- End with one line reminding the user to consult a doctor before starting a new program."""
    return generate_text(config.GEMINI_PRO_MODEL, prompt)