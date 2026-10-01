"""Automated tests. Gemini is mocked, so no API key or internet is needed."""
import pytest
from fastapi.testclient import TestClient

from app import routes
from app.gemini_client import GeminiError, clean_text
from app.main import app

FORM = {
    "username": "Thara",
    "user_id": "thara01",
    "age": "25",
    "weight": "65",
    "goal": "muscle gain",
    "intensity": "medium",
}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(routes, "generate_workout_gemini", lambda *a, **k: "Day 1 - Chest\nPush-ups 3x10")
    monkeypatch.setattr(routes, "generate_nutrition_tip_with_flash", lambda goal: "Eat protein after workouts.")
    monkeypatch.setattr(routes, "update_workout_plan", lambda plan, fb, goal="", intensity="": "Day 1 - Cardio\nRun 20 min")
    with TestClient(app) as c:  # "with" triggers startup -> creates tables
        yield c


def test_home_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Generate Plan" in r.text


def test_generate_workout(client):
    r = client.post("/generate-workout", data=FORM)
    assert r.status_code == 200
    assert "Push-ups 3x10" in r.text
    assert "Eat protein after workouts." in r.text


def test_invalid_input_is_rejected(client):
    bad = {**FORM, "age": "abc"}
    r = client.post("/generate-workout", data=bad)
    assert r.status_code == 422
    assert "age" in r.text


def test_feedback_updates_plan(client):
    client.post("/generate-workout", data=FORM)
    r = client.post("/submit-feedback", data={"user_id": "thara01", "feedback": "more cardio please"})
    assert r.status_code == 200
    assert "Run 20 min" in r.text
    assert "UPDATED" in r.text


def test_feedback_unknown_user(client):
    r = client.post("/submit-feedback", data={"user_id": "ghost", "feedback": "more cardio"})
    assert r.status_code == 404
    assert "No plan found" in r.text


def test_view_all_users_and_delete(client):
    client.post("/generate-workout", data=FORM)
    r = client.get("/view-all-users")
    assert "thara01" in r.text and "Push-ups 3x10" in r.text
    client.post("/delete-user/thara01", follow_redirects=True)
    assert "thara01" not in client.get("/view-all-users").text


def test_json_api(client):
    payload = {"username": "Ravi", "user_id": "ravi1", "age": 30, "weight": 80, "goal": "weight loss", "intensity": "high"}
    r = client.post("/api/generate-workout", json=payload)
    assert r.status_code == 200
    assert r.json()["workout_plan"].startswith("Day 1")
    r = client.post("/api/submit-feedback", json={"user_id": "ravi1", "feedback": "add yoga"})
    assert r.json()["is_updated"] is True
    assert any(u["user_id"] == "ravi1" for u in client.get("/api/users").json())


def test_gemini_failure_shows_error(client, monkeypatch):
    def boom(*a, **k):
        raise GeminiError("API key invalid")

    monkeypatch.setattr(routes, "generate_workout_gemini", boom)
    r = client.post("/generate-workout", data={**FORM, "user_id": "fail1"})
    assert r.status_code == 502
    assert "API key invalid" in r.text


def test_clean_text_removes_markdown():
    assert clean_text("**Day 1**\n* squat") == "Day 1\n• squat"