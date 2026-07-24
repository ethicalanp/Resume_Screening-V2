from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import candidate, hr


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating database tables...")
    init_db()
    yield


app = FastAPI(
    title="Resume Screener",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(candidate.router)
app.include_router(hr.router)


@app.get("/")
def home():
    return {"message": "Resume Screener Running"}
