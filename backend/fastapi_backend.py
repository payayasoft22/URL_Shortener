import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime, timezone
import random
import string

# --- 1. CONFIGURATION AND INITIALIZATION ---
# NOTE: The 'backend' directory is typically the current working directory (CWD)
# when running uvicorn. The '..' prefix tells the script to look one directory up
# (in the 'URL_Shortener' root folder) to find the JSON key.
SERVICE_ACCOUNT_KEY_PATH = "../serviceAccountKey.json"

# Initialize Firebase Admin SDK
try:
    # Check if the file exists before trying to load it
    if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
        raise FileNotFoundError(f"Service account key not found at: {SERVICE_ACCOUNT_KEY_PATH}")

    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    # Check if app is already initialized (important for --reload)
    if not firebase_admin._apps:
        firebase_app = firebase_admin.initialize_app(cred)
    else:
        firebase_app = firebase_admin.get_app()

    db = firestore.client(firebase_app)
    print("Firebase Admin SDK successfully initialized.")

except Exception as e:
    # The error from your last message will be caught here if the path is wrong
    print(f"❌ FATAL ERROR: Failed to initialize Firebase Admin SDK. Please check path and file name: {e}")


# --- 2. Pydantic Models for Data Validation ---
class AuthRequest(BaseModel):
    email: str
    password: str


class ShortenRequest(BaseModel):
    original_url: str = Field(..., description="The long URL to be shortened.")
    user_id: str = Field(..., description="The authenticated user ID.")


class UrlInfo(BaseModel):
    short_code: str
    original_url: str
    clicks: int = 0
    created_at: str


# --- 3. FastAPI App Initialization ---
app = FastAPI(title="Shortly URL Shortener API", version="1.0")


# --- 4. Helper Functions ---
def generate_short_code(length=6):
    """Generates a random, unique short code."""
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choice(characters) for i in range(length))
        # Check if code already exists in Firestore (simple check)
        if db.collection("short_urls").document(code).get().exists is False:
            return code


# --- 5. AUTHENTICATION ENDPOINTS (Used by PyQt5 AuthApp) ---

@app.post("/api/signup")
def signup_user(request: AuthRequest):
    """Creates a new user in Firebase Auth and generates the verification link."""
    if not firebase_admin._apps:
        raise HTTPException(status_code=500, detail="Server initialization failed. Firebase not available.")

    try:
        # 1. Create the user in Firebase Auth
        user = auth.create_user(
            email=request.email,
            password=request.password,
            email_verified=False
        )

        # 2. Generate the email verification link (Firebase handles the email content)
        # NOTE: The action URL is configured in the Firebase console.
        verification_link = auth.generate_email_verification_link(request.email)

        return {
            "message": "User created. Verification link generated.",
            "user_id": user.uid,
            # PyQt5 app will open this link in the browser.
            "verification_link": verification_link
        }

    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Email already in use.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signup failed: {e}")


@app.post("/api/login")
def login_user(request: AuthRequest):
    """
    Placeholder login. In a production app, this should check if the email
    is verified and use a secure token exchange. Here, we just check for user existence.
    """
    try:
        # Use Admin SDK to fetch user by email
        user = auth.get_user_by_email(request.email)

        # For this simple implementation, we assume if the user is retrieved,
        # and the password was supplied, the local app should proceed.
        # REALITY CHECK: THIS IS INSECURE FOR PASSWORD CHECKING.
        # A proper app would exchange credentials for an ID token here.

        return {"message": "Login successful", "user_id": user.uid}

    except auth.UserNotFoundError:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login failed: {e}")


# --- 6. URL SHORTENER ENDPOINTS (Used by PyQt5 HomeWindow) ---

@app.post("/api/shorten")
def create_short_url(request: ShortenRequest):
    """Shortens a URL and saves it to Firestore."""
    if not request.original_url.startswith('http'):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    try:
        code = generate_short_code()

        url_data = {
            "original_url": request.original_url,
            "user_id": request.user_id,
            "clicks": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "short_code": code
        }

        # Save to Firestore
        db.collection("short_urls").document(code).set(url_data)

        return {"short_code": code, "full_short_url": f"http://127.0.0.1:8000/r/{code}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to shorten URL: {e}")


@app.get("/api/urls/{user_id}", response_model=List[UrlInfo])
def get_user_urls(user_id: str):
    """Fetches all shortened URLs belonging to a specific user from Firestore."""
    try:
        # Query Firestore for documents where user_id matches
        urls_ref = db.collection("short_urls").where("user_id", "==", user_id).stream()

        urls_list = []
        for doc in urls_ref:
            data = doc.to_dict()
            urls_list.append(UrlInfo(**data))

        return urls_list

    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching URLs for user {user_id}: {e}")
        # Return an empty list on error instead of raising 500, to keep the UI running
        return []


# --- 7. REDIRECT ENDPOINT (Simulates the short URL logic) ---

@app.get("/r/{short_code}")
def redirect_to_long_url(short_code: str):
    """Endpoint to redirect the short code to the original URL."""
    try:
        doc_ref = db.collection("short_urls").document(short_code)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Short URL not found.")

        data = doc.to_dict()
        original_url = data.get("original_url")
        clicks = data.get("clicks", 0) + 1

        # Increment click count in Firestore
        doc_ref.update({"clicks": clicks})

        # Perform the redirect
        from starlette.responses import RedirectResponse
        return RedirectResponse(url=original_url, status_code=307)

    except Exception as e:
        # Handle errors, e.g., if Firestore is down
        raise HTTPException(status_code=500, detail=f"Redirect failed: {e}")

# To run the FastAPI server, navigate to the 'backend' folder and execute:
# uvicorn fastapi_backend:app --reload --port 8000