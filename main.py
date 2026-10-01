"""Convenience launcher so both `uvicorn main:app` and `python main.py` work."""
from app.main import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
    