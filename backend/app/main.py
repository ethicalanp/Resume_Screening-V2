from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import candidate,hr

app=FastAPI(title="Resume Screener ")

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
    return {"message":"Resume Screener Running "}
