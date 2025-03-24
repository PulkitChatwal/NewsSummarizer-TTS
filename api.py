from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from utils import generate_report
from pydantic import BaseModel
import os

app = FastAPI(title="News Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CompanyRequest(BaseModel):
    name: str

@app.post("/analyze")
async def analyze_news(request: CompanyRequest):
    try:
        report, audio_path = generate_report(request.name)
        return {
            "report": report,
            "audio_available": bool(audio_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)