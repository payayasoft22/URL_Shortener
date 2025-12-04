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
    # For Firebase Admin SDK, you can use a service account JSON file
    # or environment variables
    service_account_info = {
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
    }

    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

app = FastAPI(title="Shortly API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
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


# Helper functions
def generate_short_code(length=6):
    """Generate a random short code"""
    # Use URL-safe characters
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def parse_expiration(expiration_str: str) -> int:
    """Convert expiration string to days"""
    if expiration_str.lower() == "never":
        return 365 * 100  # 100 years for "never"
    elif "days" in expiration_str:
        try:
            return int(expiration_str.split()[0])
        except:
            return 30
    elif expiration_str.lower() == "7 days":
        return 7
    return 30  # default


def is_url_valid(url: str) -> bool:
    """Validate URL format"""
    # Add https:// if no protocol is specified
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        return validators.url(url)
    except:
        return False


def check_alias_exists(alias: str) -> bool:
    """Check if alias already exists in Firestore"""
    if not alias:
        return False

    urls_ref = db.collection('urls')
    query = urls_ref.where('short_code', '==', alias).limit(1).stream()

    for doc in query:
        if doc.exists:
            return True
    return False


@app.post("/api/shorten", response_model=ShortUrlResponse)
async def create_short_url(request: CreateShortUrlRequest):
    # Validate URL
    original_url = request.original_url
    if not original_url.startswith(('http://', 'https://')):
        original_url = 'https://' + original_url

    if not is_url_valid(original_url):
        raise HTTPException(status_code=400, detail="Invalid URL format")

    # Generate or use alias
    if request.alias:
        short_code = request.alias
        # Check if alias exists
        if check_alias_exists(short_code):
            raise HTTPException(status_code=409, detail="Alias already exists")
    else:
        # Generate unique short code
        while True:
            short_code = generate_short_code()
            if not check_alias_exists(short_code):
                break

    # Parse expiration
    expiration_days = parse_expiration(request.expiration)

    # Prepare Firestore document
    url_data = {
        'original_url': original_url,
        'short_code': short_code,
        'alias': request.alias,
        'expiration_days': expiration_days,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP,
        'clicks': 0,
        'user_id': request.user_id,
        'is_active': True
    }

    # Add expiration date if not "never"
    if expiration_days != 36500:
        expires_at = datetime.now() + timedelta(days=expiration_days)
        url_data['expires_at'] = expires_at

    # Save to Firestore
    try:
        doc_ref = db.collection('urls').document(short_code)
        doc_ref.set(url_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Build response
    short_url = f"http://localhost:8000/{short_code}"  # In production, use your domain

    return ShortUrlResponse(
        short_url=short_url,
        original_url=original_url,
        alias=request.alias,
        expiration=request.expiration,
        created_at=datetime.now().isoformat(),
        short_code=short_code
    )


@app.get("/{short_code}")
async def redirect_url(short_code: str):
    """Redirect to original URL and track clicks"""
    try:
        doc_ref = db.collection('urls').document(short_code)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="URL not found")

        url_data = doc.to_dict()

        # Check if URL is expired
        if 'expires_at' in url_data and url_data['expires_at'] < datetime.now():
            raise HTTPException(status_code=410, detail="URL has expired")

        # Increment click count
        doc_ref.update({
            'clicks': firestore.Increment(1),
            'last_accessed': firestore.SERVER_TIMESTAMP
        })

        # Return redirect (FastAPI will handle this differently)
        # In a real implementation, you'd use RedirectResponse
        return {"redirect_to": url_data['original_url']}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            # Convert Firestore timestamp to string
            if 'created_at' in data:
                data['created_at'] = data['created_at'].isoformat() if hasattr(data['created_at'],
                                                                               'isoformat') else str(data['created_at'])
            urls.append(data)

        return urls
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)