from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine, migrate_sqlite
from app.models import User
from app.routers import ai, auth, charts, dashboards, datasets, public, ws
from app.security import hash_password

Base.metadata.create_all(bind=engine)
migrate_sqlite()


def seed_demo_user() -> None:
    db = SessionLocal()
    try:
        exists = db.query(User).filter(User.username == settings.demo_username).first()
        if not exists:
            db.add(
                User(
                    username=settings.demo_username,
                    hashed_password=hash_password(settings.demo_password),
                )
            )
            db.commit()
    finally:
        db.close()


seed_demo_user()

app = FastAPI(title=settings.app_name)

origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(charts.router)
app.include_router(ai.router)
app.include_router(dashboards.router)
app.include_router(public.router)
app.include_router(ws.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "name": settings.app_name, "llm": settings.llm_provider}
