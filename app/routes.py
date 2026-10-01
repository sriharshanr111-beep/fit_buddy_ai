"""All FitBuddy routes: HTML pages + JSON API."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
import os

from . import config
from .database import (
    delete_user,
    get_all_users,
    get_original_plan,
    get_plan,
    get_session,
    get_user,
    save_plan,
    save_user,
    update_plan,
)
from .gemini_client import GeminiError
from .gemini_flash_generator import generate_nutrition_tip_with_flash
from .gemini_generator import generate_workout_gemini
from .schemas import FeedbackRequest, UserInput
from .updated_plan import update_workout_plan

router = APIRouter()

TEMPLATE_DIR = os.path.join(config.BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

FALLBACK_TIPS = {
    "weight loss": "Build meals around lean protein and vegetables, and drink water before meals to help control portions.",
    "muscle gain": "Include protein in your post-workout meal and get 7-9 hours of sleep so your muscles can recover.",
    "general wellness": "Aim for a balanced plate with vegetables, whole grains and protein, and stay hydrated through the day.",
    "flexibility": "Stay hydrated and add a few minutes of gentle stretching after workouts to support recovery.",
    "endurance": "Eat carbohydrates before long sessions and replace fluids and electrolytes afterwards.",
}


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


def _format_validation_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        field = ".".join(str(x) for x in err.get("loc", []))
        parts.append(f"{field}: {err.get('msg', 'invalid value')}")
    return "; ".join(parts)


# ------------------------------------------------------------------ core logic
def create_plan(db, data: UserInput) -> dict:
    """Generate workout + tip with Gemini, store everything, return template context."""
    try:
        workout = generate_workout_gemini(data.username, data.age, data.weight, data.goal, data.intensity)
    except GeminiError as exc:
        raise AppError(str(exc), 502)

    try:
        tip = generate_nutrition_tip_with_flash(data.goal)
    except GeminiError:
        tip = FALLBACK_TIPS.get(data.goal, "Stay hydrated, eat enough protein and get enough sleep.")

    user = save_user(db, data.user_id, data.username, data.age, data.weight, data.goal, data.intensity)
    plan = save_plan(db, data.user_id, workout, tip)
    return build_context(user, plan, message="Your personalized plan is ready!")


def apply_feedback(db, data: FeedbackRequest) -> dict:
    user = get_user(db, data.user_id)
    original = get_original_plan(db, data.user_id)
    if user is None or original is None:
        raise AppError(f"No plan found for User ID '{data.user_id}'. Generate a plan first.", 404)

    plan = get_plan(db, data.user_id)
    base_plan = plan.updated_plan or original  # refine the latest version
    try:
        new_plan = update_workout_plan(base_plan, data.feedback, user.goal, user.intensity)
    except GeminiError as exc:
        raise AppError(str(exc), 502)

    try:
        tip = generate_nutrition_tip_with_flash(user.goal)
    except GeminiError:
        tip = None  # keep the previous tip

    plan = update_plan(db, data.user_id, new_plan, data.feedback, tip)
    return build_context(user, plan, message="Your plan was updated based on your feedback!")


def build_context(user, plan, message: str = "") -> dict:
    current = plan.updated_plan or plan.original_plan
    return {
        "username": user.username,
        "user_id": user.user_id,
        "age": user.age,
        "weight": user.weight,
        "goal": user.goal,
        "intensity": user.intensity,
        "workout_plan": current,
        "original_plan": plan.original_plan,
        "is_updated": bool(plan.updated_plan),
        "nutrition_tip": plan.nutrition_tip or "",
        "last_feedback": plan.last_feedback or "",
        "message": message,
    }


def _index(request: Request, error: str = "", form: dict | None = None, status_code: int = 200):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"goals": config.GOALS, "intensities": config.INTENSITIES, "error": error, "form": form or {}},
        status_code=status_code,
    )


# ------------------------------------------------------------------ HTML pages
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return _index(request)


@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout(
    request: Request,
    username: str = Form(""),
    user_id: str = Form(""),
    age: str = Form(""),
    weight: str = Form(""),
    goal: str = Form(""),
    intensity: str = Form(""),
    db=Depends(get_db),
):
    form = dict(username=username, user_id=user_id, age=age, weight=weight, goal=goal, intensity=intensity)
    try:
        data = UserInput(**form)
    except ValidationError as exc:
        return _index(request, _format_validation_error(exc), form, 422)

    try:
        context = create_plan(db, data)
    except AppError as exc:
        return _index(request, exc.message, form, exc.status_code)
    return templates.TemplateResponse(request, "result.html", context)


@router.get("/feedback", response_class=HTMLResponse)
def feedback_page(request: Request, user_id: str = ""):
    return templates.TemplateResponse(request, "feedback.html", {"user_id": user_id, "error": ""})


@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback(
    request: Request,
    user_id: str = Form(""),
    feedback: str = Form(""),
    db=Depends(get_db),
):
    try:
        data = FeedbackRequest(user_id=user_id, feedback=feedback)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "feedback.html",
            {"user_id": user_id, "feedback": feedback, "error": _format_validation_error(exc)},
            status_code=422,
        )
    try:
        context = apply_feedback(db, data)
    except AppError as exc:
        return templates.TemplateResponse(
            request,
            "feedback.html",
            {"user_id": user_id, "feedback": feedback, "error": exc.message},
            status_code=exc.status_code,
        )
    return templates.TemplateResponse(request, "result.html", context)


@router.get("/plan/{user_id}", response_class=HTMLResponse)
def view_plan(request: Request, user_id: str, db=Depends(get_db)):
    user = get_user(db, user_id)
    plan = get_plan(db, user_id)
    if user is None or plan is None:
        return _index(request, f"No plan found for User ID '{user_id}'.", {}, 404)
    return templates.TemplateResponse(request, "result.html", build_context(user, plan))


@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request, db=Depends(get_db)):
    users = get_all_users(db)
    return templates.TemplateResponse(request, "all_users.html", {"users": users})


@router.post("/delete-user/{user_id}")
def delete_user_route(user_id: str, db=Depends(get_db)):
    delete_user(db, user_id)
    return RedirectResponse("/view-all-users", status_code=303)


# ------------------------------------------------------------------ JSON API
@router.post("/api/generate-workout")
def api_generate_workout(data: UserInput, db=Depends(get_db)):
    try:
        return create_plan(db, data)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/api/submit-feedback")
def api_submit_feedback(data: FeedbackRequest, db=Depends(get_db)):
    try:
        return apply_feedback(db, data)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get("/api/users")
def api_users(db=Depends(get_db)):
    result = []
    for u in get_all_users(db):
        result.append(
            {
                "user_id": u.user_id,
                "username": u.username,
                "age": u.age,
                "weight": u.weight,
                "goal": u.goal,
                "intensity": u.intensity,
                "original_plan": u.plan.original_plan if u.plan else None,
                "updated_plan": u.plan.updated_plan if u.plan else None,
            }
        )
    return result


@router.get("/health")
def health():
    return {"status": "ok", "api_key_configured": bool(config.GOOGLE_API_KEY)}