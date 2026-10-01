"""Feedback-based plan refinement (uses the 'pro' Gemini model)."""
from . import config
from .gemini_client import generate_text


def update_workout_plan(original_plan: str, feedback: str, goal: str = "", intensity: str = "") -> str:
    prompt = f"""You are an experienced certified personal trainer.
Below is a user's current 7-day workout plan and their feedback.
Rewrite the FULL 7-day plan so it applies the feedback while keeping the user's goal and intensity.

Goal: {goal}
Intensity: {intensity}

CURRENT PLAN:
{original_plan}

USER FEEDBACK:
{feedback}

Rules:
- Return the complete updated plan for Day 1 to Day 7 using the same layout as the current plan
  (Day N - Focus / Warm-up / Main workout / Cooldown).
- Use PLAIN TEXT only. No markdown, asterisks, or tables.
- Do not add any introduction; start directly with Day 1."""
    return generate_text(config.GEMINI_PRO_MODEL, prompt)