from fastapi import FastAPI

app = FastAPI(
    title="CareerPilot AI API",
    description="CareerPilot AI 后端服务",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"message": "CareerPilot AI API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "CareerPilot AI API"}
