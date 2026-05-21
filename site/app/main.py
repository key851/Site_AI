from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import pages
from app.settings import settings


app = FastAPI(title=settings.app_name, debug=settings.debug)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}