"""Top-level FastAPI entry point re-exporting `app` from `app.main`."""

from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    # Bind strictly to 127.0.0.1 for local execution safety
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)

