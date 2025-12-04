from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateShortUrlRequest(BaseModel):
    original_url: str
    alias: Optional[str] = None
    expiration: str = "30 days"
    user_id: Optional[str] = None

class ShortUrlResponse(BaseModel):
    short_url: str
    original_url: str
    alias: Optional[str] = None
    expiration: str
    created_at: str
    short_code: str

# In-memory storage for testing
urls_db = {}

@app.post("/api/shorten", response_model=ShortUrlResponse)
async def create_short_url(request: CreateShortUrlRequest):
    import uuid
    import datetime

    # Generate short code
    if request.alias:
        short_code = request.alias
        if short_code in urls_db:
            return {"error": "Alias already exists"}
    else:
        short_code = str(uuid.uuid4())[:8]

    # Store in memory
    urls_db[short_code] = {
        "original_url": request.original_url,
        "alias": request.alias,
        "expiration": request.expiration,
        "user_id": request.user_id,
        "created_at": datetime.datetime.now().isoformat(),
        "clicks": 0
    }

    short_url = f"http://localhost:8000/{short_code}"

    return ShortUrlResponse(
        short_url=short_url,
        original_url=request.original_url,
        alias=request.alias,
        expiration=request.expiration,
        created_at=datetime.datetime.now().isoformat(),
        short_code=short_code
    )

@app.get("/api/urls/{user_id}")
async def get_user_urls(user_id: str):
    user_urls = [{"id": k, **v} for k, v in urls_db.items() if v.get("user_id") == user_id]
    return user_urls

if __name__ == "__main__":
    import uvicorn
    print("Starting test server on http://localhost:8000")
    print("Test endpoint: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)