import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import (
    critic_chain,
    generate_report,
    run_reader_agent,
    run_search_agent,
)

app = FastAPI(title="ResearchMind API", version="1.0.0")

allowed_origins = [
    "https://raomuhammadrizwan225.github.io",
    "http://127.0.0.1:8501",
    "http://localhost:8501",
]

extra_origin = os.getenv("FRONTEND_ORIGIN", "").strip()
if extra_origin and extra_origin not in allowed_origins:
    allowed_origins.append(extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    topic: str

class ReaderRequest(BaseModel):
    topic: str
    search_results: str

class WriterRequest(BaseModel):
    topic: str
    search_results: str
    reader_results: str

class CriticRequest(BaseModel):
    report: str

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/search")
def search(request: SearchRequest):
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Research topic is required.")
    try:
        return {"result": run_search_agent(topic)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/api/reader")
def reader(request: ReaderRequest):
    topic = request.topic.strip()
    search_results = request.search_results.strip()
    if not topic or not search_results:
        raise HTTPException(status_code=400, detail="Topic and search results are required.")
    try:
        return {"result": run_reader_agent(topic, search_results)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/api/writer")
def writer(request: WriterRequest):
    topic = request.topic.strip()
    search_results = request.search_results.strip()
    reader_results = request.reader_results.strip()
    if not topic or not reader_results:
        raise HTTPException(status_code=400, detail="Topic and reader results are required.")
    research_material = (
        f"SEARCH RESULTS:\n{search_results}\n\n"
        f"READER SUMMARIES:\n{reader_results}"
    )
    try:
        return {"result": generate_report(topic, research_material)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/api/critic")
def critic(request: CriticRequest):
    report = request.report.strip()
    if not report:
        raise HTTPException(status_code=400, detail="Report is required.")
    try:
        return {"result": critic_chain.invoke({"report": report})}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
