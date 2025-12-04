from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
import secrets
from datetime import datetime, timedelta
import validators
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
if not firebase_admin._apps:
    # Use service account JSON or environment variables
    cred = credentials.Certificate("url-shortener-c2632-firebase-adminsdk-fbsvc-c9980498ad.json")  # Or use env vars
    firebase_admin.initialize_app(cred)

db = firestore.client()

app = FastAPI(title="Shortly API")

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


def generate_short_code(length=6):
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def parse_expiration(expiration_str: str) -> int:
    if expiration_str.lower() == "never":
        return 365 * 100
    elif "days" in expiration_str:
        try:
            return int(expiration_str.split()[0])
        except:
            return 30
    return 30


@app.post("/api/shorten", response_model=ShortUrlResponse)
async def create_short_url(request: CreateShortUrlRequest):
    # Validate URL
    original_url = request.original_url
    if not original_url.startswith(('http://', 'https://')):
        original_url = 'https://' + original_url

    if not validators.url(original_url):
        raise HTTPException(status_code=400, detail="Invalid URL format")

    # Generate or use alias
    if request.alias:
        short_code = request.alias
        # Check if alias exists
        existing = db.collection('urls').document(short_code).get()
        if existing.exists:
            raise HTTPException(status_code=409, detail="Alias already exists")
    else:
        # Generate unique short code
        while True:
            short_code = generate_short_code()
            existing = db.collection('urls').document(short_code).get()
            if not existing.exists:
                break

    # Parse expiration
    expiration_days = parse_expiration(request.expiration)

    # Prepare data
    url_data = {
        'original_url': original_url,
        'short_code': short_code,
        'alias': request.alias,
        'expiration_days': expiration_days,
        'created_at': firestore.SERVER_TIMESTAMP,
        'clicks': 0,
        'user_id': request.user_id,
        'is_active': True
    }

    # Add expiration date
    if expiration_days != 36500:
        expires_at = datetime.now() + timedelta(days=expiration_days)
        url_data['expires_at'] = expires_at

    # Save to Firestore
    try:
        db.collection('urls').document(short_code).set(url_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Return response
    short_url = f"http://localhost:8000/{short_code}"

    return ShortUrlResponse(
        short_url=short_url,
        original_url=original_url,
        alias=request.alias,
        expiration=request.expiration,
        created_at=datetime.now().isoformat(),
        short_code=short_code
    )


@app.get("/api/urls/{user_id}")
async def get_user_urls(user_id: str):
    """Get all URLs for a specific user"""
    try:
        urls_ref = db.collection('urls')
        query = urls_ref.where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)

        urls = []
        for doc in query.stream():
            data = doc.to_dict()
            data['id'] = doc.id
            # Convert timestamps
            if 'created_at' in data:
                data['created_at'] = data['created_at'].isoformat() if hasattr(data['created_at'],
                                                                               'isoformat') else str(data['created_at'])
            if 'expires_at' in data and data['expires_at']:
                data['expires_at'] = data['expires_at'].isoformat() if hasattr(data['expires_at'],
                                                                               'isoformat') else str(data['expires_at'])
            urls.append(data)

        return urls
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)