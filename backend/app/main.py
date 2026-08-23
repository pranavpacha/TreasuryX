from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import bonds, cv, fx, market3d, overview, positions, risk, scenario, yield_curve
from app.config import settings
from app.database import SessionLocal, init_db
from app.seed import seed_all


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="TreasuryX API",
    description="Educational/simulated Treasury market intelligence & trading terminal API. "
                "No real-money trading. All data is DEMO/SIMULATED unless otherwise labeled.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router)
app.include_router(fx.router)
app.include_router(bonds.router)
app.include_router(positions.router)
app.include_router(yield_curve.router)
app.include_router(risk.router)
app.include_router(scenario.router)
app.include_router(cv.router)
app.include_router(market3d.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment, "data_mode": settings.data_mode}
