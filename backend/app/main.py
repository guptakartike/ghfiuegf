from fastapi import FastAPI

app = FastAPI(
    title="Wind Analytics API",
    version="1.0.0",
)

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy"}