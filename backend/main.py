from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.responses import JSONResponse
from fastapi import status as http_status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import os
from threading import Lock
from datetime import datetime, timedelta
import google.generativeai as genai
from pathlib import Path
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import re
import hashlib
import hmac
import base64
import secrets
from dotenv import load_dotenv

# Initialize FastAPI app
load_dotenv()
app = FastAPI(title="AI Feedback System API", version="1.0.0")

# CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini API (using same model as Task 1)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemma-3-12b-it")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
else:
    model = None

# Data storage file
DATA_FILE = Path(__file__).parent / "submissions.json"

# Users storage file
USERS_FILE = Path(__file__).parent / "users.json"

# AI timeout (seconds). Lower default so users don't wait too long; can be overridden via env.
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "5"))
AI_MAX_WORKERS = int(os.getenv("AI_MAX_WORKERS", "2"))
AI_MAX_OUTPUT_TOKENS = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "512"))
_ai_executor = ThreadPoolExecutor(max_workers=AI_MAX_WORKERS)

# Ensure data file exists
if not DATA_FILE.exists():
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

# Ensure users file exists
if not USERS_FILE.exists():
    with open(USERS_FILE, "w") as f:
        json.dump([], f)

# Simple lock to avoid concurrent writes to the submissions file
submissions_lock = Lock()

# Simple lock to avoid concurrent writes to the users file
users_lock = Lock()

# Token secret
AUTH_TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET", "dev-secret-change-me")

DEBUG_REQUEST_LOGS = os.getenv("DEBUG_REQUEST_LOGS", "0") == "1"

_submissions_cache_mtime: Optional[float] = None
_submissions_cache_data: List[dict] = []

@app.middleware("http")
async def _request_timing_middleware(request, call_next):
    if not DEBUG_REQUEST_LOGS:
        return await call_next(request)
    start = perf_counter()
    response = await call_next(request)
    elapsed_ms = int((perf_counter() - start) * 1000)
    print(f"{request.method} {request.url.path} -> {response.status_code} ({elapsed_ms}ms)")
    return response

def _atomic_write_json(path: Path, data: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)

def _generate_content_with_timeout(prompt: str):
    if model is None:
        return None
    generation_config = {
        "max_output_tokens": AI_MAX_OUTPUT_TOKENS,
        # Low temperature for stable, repeatable outputs for the same input.
        "temperature": 0.0,
        "top_p": 1,
    }
    future = _ai_executor.submit(model.generate_content, prompt, generation_config=generation_config)
    try:
        return future.result(timeout=AI_TIMEOUT_SECONDS)
    except FuturesTimeoutError:
        return None
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

def extract_json_strong(raw: str) -> Optional[dict]:
    if not raw or not isinstance(raw, str):
        return None
    cleaned = raw.strip()

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    try:
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if not m:
            return None
        candidate = m.group(0)
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None

def _predict_stars_from_text_heuristic(rating: int, review_text: str) -> Optional[int]:
    text = (review_text or "").lower()
    if not text.strip():
        try:
            return int(rating) if 1 <= int(rating) <= 5 else None
        except Exception:
            return None

    strong_pos = [
        "amazing",
        "excellent",
        "outstanding",
        "perfect",
        "incredible",
        "fantastic",
        "love",
        "highly recommend",
    ]
    soft_pos = [
        "good",
        "tasty",
        "fresh",
        "nice",
        "friendly",
        "enjoyed",
        "satisfied",
        "would come back",
    ]
    strong_neg = [
        "terrible",
        "horrible",
        "awful",
        "worst",
        "disgusting",
        "never again",
        "ruined",
        "unacceptable",
    ]
    soft_neg = [
        "bad",
        "cold",
        "slow",
        "rude",
        "disappointed",
        "disappointing",
        "overpriced",
        "not good",
    ]

    score = 0
    for word in strong_pos:
        if word in text:
            score += 2
    for word in soft_pos:
        if word in text:
            score += 1
    for word in strong_neg:
        if word in text:
            score -= 2
    for word in soft_neg:
        if word in text:
            score -= 1

    try:
        base = int(rating)
        if not (1 <= base <= 5):
            base = 3
    except Exception:
        base = 3

    if score >= 4:
        return 5
    if score == 3:
        return 4
    if score == 2:
        return 4 if base >= 4 else 3
    if score == 1:
        return 3 if base <= 3 else 4
    if score == 0:
        return base
    if score == -1:
        return 2 if base <= 3 else 3
    if score <= -2:
        return 1
    return base


def _instant_ai_pack(rating: int, review_text: str, username: Optional[str]) -> Dict[str, Any]:
    name = username or "there"
    snippet = " ".join(str(review_text).strip().split()[:18]).strip()
    if snippet and not snippet.endswith((".", "!", "?")):
        snippet += "..."

    # Use text-driven sentiment (predicted_stars) when available so tone matches the review text,
    # not just the numeric rating.
    try:
        sentiment_based = _predict_stars_from_text_heuristic(rating, review_text)
    except Exception:
        sentiment_based = None

    try:
        base_rating = int(rating)
        if not (1 <= base_rating <= 5):
            base_rating = 3
    except Exception:
        base_rating = 3

    effective_rating = sentiment_based if sentiment_based is not None else base_rating

    if effective_rating <= 2:
        # Clearly negative feeling text: apologize, give hope, promise improvement.
        ai_response = (
            f"Hi {name}, thank you for telling us about your experience. I'm really sorry things did not go well. "
            f"We take feedback like '{snippet or 'your review'}' seriously and we'll work with our team to fix these issues. "
            "We hope you'll give us another chance so we can make your next visit much better."
        )
        ai_actions = (
            "Here is a quick action plan based on this negative experience:\n"
            "1. Investigate the specific problems mentioned in the review and document the root causes so the team clearly understands what went wrong.\n"
            "2. Provide targeted coaching or refresher training for the staff involved, focusing on service recovery, communication, and food quality standards.\n"
            "3. Proactively follow up with the customer, explain the corrective steps you are taking, and offer a recovery gesture (apology, replacement, or discount) to rebuild trust."
        )
        ai_summary = (
            f"Customer gave a {rating}-star rating and the review feels **negative**. "
            f"Key issue described: **{snippet or 'no clear details provided'}**."
        )
    elif effective_rating == 3:
        # Mixed or neutral text: acknowledge both good and bad, show intent to improve.
        ai_response = (
            f"Thank you {name} for the honest and balanced feedback. "
            f"You mentioned '{snippet or 'both positives and negatives'}', and we'll use this to improve. "
            "We appreciate you giving us a chance and hope your next visit will feel even better."
        )
        ai_actions = (
            "Here is a balanced improvement plan for this mixed review:\n"
            "1. Identify the main friction point mentioned (for example, speed, consistency, or communication) and create a small experiment or SOP change to address it over the next 1–2 weeks.\n"
            "2. Preserve the strengths the customer liked by sharing those positives with the team and building them into your standard operating procedures.\n"
            "3. Monitor reviews with similar themes and track before/after ratings so you can confirm whether the changes are actually improving the guest experience."
        )
        ai_summary = (
            f"Customer gave a {rating}-star rating and the review sounds **mixed/neutral**. "
            f"Main points: **{snippet or 'no clear details provided'}**."
        )
    else:
        # Positive feeling text: strong thanks, happy they are a customer, still improving.
        ai_response = (
            f"Thank you {name} for such a wonderful review and the {rating}-star rating! "
            f"We're really happy you enjoyed your visit, especially your note: '{snippet or 'your kind words'}'. "
            "We're grateful to have you as a customer and we're still improving our service every day to make your future visits even better."
        )
        ai_actions = (
            "Here is how you can turn this positive feedback into long-term value:\n"
            "1. Share this review with the full team to recognize their effort, and call out any specific individuals or shifts that contributed so they feel appreciated.\n"
            "2. Document what went especially well (speed, flavor, friendliness, ambiance) and turn those behaviors into clear standards or checklists for every shift.\n"
            "3. Use this review in your marketing or in-store signage (with permission), and train staff to invite similarly satisfied guests to leave their own reviews to build momentum."
        )
        ai_summary = (
            f"Customer gave a {rating}-star rating and the review feels **positive**. "
            f"Key praise: **{snippet or 'no extra details provided'}**."
        )

    # For instant packs, keep predicted_stars simple but valid.
    predicted_stars: Optional[int] = effective_rating
    if predicted_stars is None:
        try:
            predicted_stars = int(rating)
        except Exception:
            predicted_stars = 3

    if not (1 <= int(predicted_stars) <= 5):
        predicted_stars = 3

    return {
        "ai_response": ai_response,
        "ai_summary": ai_summary,
        "ai_recommended_actions": ai_actions,
        "predicted_stars": int(predicted_stars),
        "prediction_explanation": "Prediction approximated from the text sentiment and given rating for a fast response.",
    }


def _fallback_ai_pack(rating: int, review_text: str, username: Optional[str]) -> Dict[str, Any]:
    """Simple fallback when Gemini is unavailable or returns invalid output.

    This is only used when the model is not configured or there is a hard
    error. Normal flows use the Gemini few-shot JSON prompt instead.
    """
    return _instant_ai_pack(rating, review_text, username)

def generate_ai_pack(rating: int, review_text: str, username: Optional[str] = None) -> Dict[str, Any]:
    if model is None:
        return _fallback_ai_pack(rating, review_text, username)

    user_label = username or "customer"

    # Single template + few-shot prompt that drives ALL AI output consistently.
    prompt = f"""You are an AI assistant for a restaurant feedback system.

The user has submitted a review. You must analyze it and produce:
- ai_response: warm, professional message for the customer.
- ai_summary: concise summary for the admin dashboard.
- ai_recommended_actions: detailed, actionable steps for management.
- predicted_stars: sentiment-driven rating based on review_text.
- prediction_explanation: short explanation of the rating.

Return ONLY valid JSON, no markdown and no code fences, with this exact schema:
{{
  "ai_response": string,
  "ai_summary": string,
  "ai_recommended_actions": string,
  "predicted_stars": integer 1-5,
  "prediction_explanation": string
}}

======================
⭐ Rating Rubric
======================

1 Star → Very negative. Complaints, bad service, rude staff, terrible food.
2 Stars → Mostly negative. Some positives but overall disappointing.
3 Stars → Mixed or neutral. Average experience, both good and bad points.
4 Stars → Mostly positive. Good experience with minor issues.
5 Stars → Very positive. Strong praise, excellent experience.

======================
📌 Examples (Few-Shot)
======================

Example 1 (Negative):
rating_given: 1
review_text: "Terrible service. Food was cold. Waiter was rude. Never coming back."
Output:
{{
  "ai_response": "Thank you for sharing this feedback. I'm very sorry about the cold food and rude service you experienced. This is far below our standards, and we'll be reviewing this with our team so we can make things right and improve future visits.",
  "ai_summary": "Customer reported **cold food**, **rude service**, and an overall **very negative** experience.",
  "ai_recommended_actions": "1. Review the incident with the staff working during this visit and reinforce expectations for polite, attentive service.\n2. Audit kitchen-to-table timing and food temperature checks to prevent cold dishes from being served.\n3. Reach out to the customer with a sincere apology and a recovery offer to encourage them to give the restaurant another chance.",
  "predicted_stars": 1,
  "prediction_explanation": "The review is strongly negative with multiple complaints about service and food."
}}

Example 2 (Neutral / Mixed):
rating_given: 3
review_text: "Food was okay but service was slow. The ambiance was nice though."
Output:
{{
  "ai_response": "Thank you for your honest feedback. I'm glad you enjoyed the ambiance, and I'm sorry the slow service affected your experience. We'll use your comments to improve our service speed while keeping the atmosphere you liked.",
  "ai_summary": "Customer mentioned **slow service** but appreciated the **nice ambiance**, overall **mixed** experience.",
  "ai_recommended_actions": "1. Review staffing and workflow during busy periods to reduce wait times for guests.\n2. Preserve the positive aspects of the ambiance by documenting what guests consistently like.\n3. Monitor future reviews for comments about service speed to confirm whether changes are working.",
  "predicted_stars": 3,
  "prediction_explanation": "The review contains both positives and negatives, matching a mixed 3-star experience."
}}

Example 3 (Positive):
rating_given: 5
review_text: "Amazing food and great service! The staff was attentive and the chef's special was incredible. Will definitely return!"
Output:
{{
  "ai_response": "Thank you so much for this wonderful review! We're thrilled you loved the food, attentive service, and the chef's special. We're grateful to have you as a customer and look forward to welcoming you back again soon.",
  "ai_summary": "Customer praised **amazing food**, **great service**, and an **incredible chef's special**, overall **very positive** experience.",
  "ai_recommended_actions": "1. Share this feedback with both the service team and kitchen staff to recognize their effort and keep morale high.\n2. Highlight the chef's special in future promotions, as it clearly resonates with guests.\n3. Document the service and kitchen practices that led to this experience so they can be repeated consistently.",
  "predicted_stars": 5,
  "prediction_explanation": "The review is highly positive with strong praise, matching a 5-star experience."
}}

======================
🎯 Your Task
======================
Now generate output for this real review. Follow the style and structure of the examples above:

customer_name: {user_label}
rating_given: {rating}
review_text: "{review_text}"

Remember:
- Use the review_text sentiment (not only rating_given) to decide predicted_stars.
- Keep ai_response warm and empathetic.
- Keep ai_summary short (1–3 sentences) and highlight 3–6 key words with ""double comma"".
- Make ai_recommended_actions a numbered list with clear, concrete steps.
"""

    try:
        response = _generate_content_with_timeout(prompt)
        raw = (response.text or "").strip() if response else ""
        parsed = extract_json_strong(raw) or {}

        ai_response = str(parsed.get("ai_response") or "").strip()
        ai_summary = str(parsed.get("ai_summary") or "").strip()
        ai_actions = str(parsed.get("ai_recommended_actions") or "").strip()
        explanation = str(parsed.get("prediction_explanation") or "AI prediction").strip()

        predicted = parsed.get("predicted_stars")
        predicted_stars: Optional[int] = None
        try:
            if predicted is not None and predicted != "":
                predicted_int = int(predicted)
                if 1 <= predicted_int <= 5:
                    predicted_stars = predicted_int
        except Exception:
            predicted_stars = None

        if predicted_stars is None:
            predicted_stars = _predict_stars_from_text_heuristic(rating, review_text)

        if not ai_response or not ai_summary or not ai_actions:
            return _fallback_ai_pack(rating, review_text, username)

        return {
            "ai_response": ai_response,
            "ai_summary": ai_summary,
            "ai_recommended_actions": ai_actions,
            "predicted_stars": predicted_stars,
            "prediction_explanation": explanation or "AI prediction",
        }
    except Exception as e:
        print(f"Error generating AI pack: {e}")
        return _fallback_ai_pack(rating, review_text, username)

# Pydantic models
class ReviewSubmission(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Star rating from 1 to 5")
    review_text: str = Field(..., min_length=1, description="Review text content")

class SubmissionResponse(BaseModel):
    id: str
    rating: int
    review_text: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    ai_response: str
    ai_summary: str
    ai_recommended_actions: str
    predicted_stars: Optional[int] = None
    prediction_explanation: Optional[str] = None
    timestamp: str
    status: Optional[str] = None

class AuthRegisterRequest(BaseModel):
    username: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

class AuthLoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)

class AuthUserPublic(BaseModel):
    username: str
    email: str
    role: str

class AuthResponse(BaseModel):
    access_token: str
    user: AuthUserPublic

class AdminSubmission(BaseModel):
    id: str
    rating: int
    review_text: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    ai_response: str
    ai_summary: str
    ai_recommended_actions: str
    predicted_stars: Optional[int] = None
    prediction_explanation: Optional[str] = None
    timestamp: str
    status: Optional[str] = None

# Helper functions
def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

def _b64url_decode(s: str) -> bytes:
    padded = s + "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))

def load_users() -> List[dict]:
    try:
        with users_lock:
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
        return users if isinstance(users, list) else []
    except Exception as e:
        print(f"Error loading users: {e}")
        return []

def save_users(users: List[dict]) -> None:
    with users_lock:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)

def hash_password(password: str, salt: Optional[bytes] = None) -> Dict[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return {"salt": salt.hex(), "hash": dk.hex()}

def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False

def ensure_default_users() -> None:
    users = load_users()
    existing_emails = {u.get("email") for u in users}

    defaults = [
        {"username": "admin", "email": "admin@gmail.com", "password": "Admin@123", "role": "admin"},
        {"username": "user", "email": "user@gmail.com", "password": "User@123", "role": "user"},
    ]

    changed = False
    for d in defaults:
        if d["email"] in existing_emails:
            continue
        ph = hash_password(d["password"])
        users.append(
            {
                "id": f"usr_{secrets.token_hex(8)}",
                "username": d["username"],
                "email": d["email"],
                "password_salt": ph["salt"],
                "password_hash": ph["hash"],
                "role": d["role"],
                "created_at": datetime.now().isoformat(),
            }
        )
        changed = True

    if changed:
        save_users(users)

def create_access_token(payload: Dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(AUTH_TOKEN_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid token")
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(AUTH_TOKEN_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(status_code=401, detail="Invalid token")
    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(datetime.now().timestamp()):
        raise HTTPException(status_code=401, detail="Token expired")
    return payload

def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    return payload

def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

ensure_default_users()

def _load_submissions_unlocked() -> List[dict]:
    global _submissions_cache_mtime, _submissions_cache_data
    try:
        if not DATA_FILE.exists():
            return []
        mtime = DATA_FILE.stat().st_mtime
        if _submissions_cache_mtime == mtime and isinstance(_submissions_cache_data, list):
            return list(_submissions_cache_data)

        started = perf_counter()
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        elapsed_ms = int((perf_counter() - started) * 1000)

        if isinstance(raw, dict) and isinstance(raw.get("submissions"), list):
            submissions = raw.get("submissions")
        elif isinstance(raw, list):
            submissions = raw
        else:
            submissions = []

        submissions = [s for s in submissions if isinstance(s, dict)]

        # Sort newest first for consistent API responses
        submissions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        _submissions_cache_mtime = mtime
        _submissions_cache_data = list(submissions)

        if elapsed_ms > 250:
            print(f"Warning: load_submissions took {elapsed_ms}ms reading {DATA_FILE}")

        return submissions
    except Exception as e:
        print(f"Error loading submissions: {e}")
        return []

def load_submissions(already_locked: bool = False) -> List[dict]:
    if already_locked:
        return _load_submissions_unlocked()
    with submissions_lock:
        return _load_submissions_unlocked()

def save_submission(submission: dict):
    """Save submission to JSON file"""
    try:
        with submissions_lock:
            submissions = load_submissions(already_locked=True)
            submissions.append(submission)
            _atomic_write_json(DATA_FILE, submissions)
            global _submissions_cache_mtime, _submissions_cache_data
            _submissions_cache_mtime = DATA_FILE.stat().st_mtime
            _submissions_cache_data = list(submissions)
        return submission
    except Exception as e:
        print(f"Error saving submission: {e}")
        return None

def update_submission_return(submission_id: str, updates: dict):
    """Update an existing submission by id and return updated object"""
    try:
        with submissions_lock:
            submissions = load_submissions(already_locked=True)
            updated = None
            for i, s in enumerate(submissions):
                if s.get("id") == submission_id:
                    submissions[i] = {**s, **updates}
                    updated = submissions[i]
                    break
            if updated is None:
                return None
            _atomic_write_json(DATA_FILE, submissions)
            global _submissions_cache_mtime, _submissions_cache_data
            _submissions_cache_mtime = DATA_FILE.stat().st_mtime
            _submissions_cache_data = list(submissions)
            return updated
    except Exception as e:
        print(f"Error updating submission {submission_id}: {e}")
        return None

def update_submission(submission_id: str, updates: dict) -> bool:
    """Update an existing submission by id with the provided updates"""
    try:
        with submissions_lock:
            submissions = load_submissions(already_locked=True)
            updated = False
            for i, s in enumerate(submissions):
                if s.get("id") == submission_id:
                    submissions[i] = {**s, **updates}
                    updated = True
                    break
            if not updated:
                print(f"Warning: submission id {submission_id} not found for update")
                return False
            _atomic_write_json(DATA_FILE, submissions)
            global _submissions_cache_mtime, _submissions_cache_data
            _submissions_cache_mtime = DATA_FILE.stat().st_mtime
            _submissions_cache_data = list(submissions)
            return True
    except Exception as e:
        print(f"Error updating submission: {e}")
        return False

def process_submission_task(submission_id: str, rating: int, review_text: str, username: Optional[str]) -> None:
    try:
        pack = generate_ai_pack(rating, review_text, username=username)

        updates = {
            "ai_response": pack.get("ai_response", ""),
            "ai_summary": pack.get("ai_summary", ""),
            "ai_recommended_actions": pack.get("ai_recommended_actions", ""),
            "predicted_stars": pack.get("predicted_stars"),
            "prediction_explanation": pack.get("prediction_explanation", "AI prediction"),
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }
        update_submission(submission_id, updates)
    except Exception as e:
        print(f"Error processing submission {submission_id}: {e}")
        update_submission(
            submission_id,
            {
                "status": "failed",
                "ai_response": "AI processing failed. Please try again later.",
                "timestamp": datetime.now().isoformat(),
            },
        )

@app.post("/api/auth/register", response_model=AuthResponse)
async def register(req: AuthRegisterRequest):
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    users = load_users()
    if any(u.get("email") == req.email for u in users):
        raise HTTPException(status_code=400, detail="Email already registered")

    ph = hash_password(req.password)
    user = {
        "id": f"usr_{secrets.token_hex(8)}",
        "username": req.username,
        "email": req.email,
        "password_salt": ph["salt"],
        "password_hash": ph["hash"],
        "role": "user",
        "created_at": datetime.now().isoformat(),
    }
    users.append(user)
    save_users(users)

    payload = {
        "sub": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "exp": int((datetime.now() + timedelta(days=30)).timestamp()),
    }
    token = create_access_token(payload)
    return {
        "access_token": token,
        "user": {"username": user["username"], "email": user["email"], "role": user["role"]},
    }

@app.post("/api/submit-review", response_model=SubmissionResponse)
async def submit_review(payload: ReviewSubmission):
    """Submit a review and synchronously generate AI output via Gemini.

    This endpoint calls generate_ai_pack once using the Template + Few-Shot
    prompt so that:
    - The user immediately gets the Gemini-generated ai_response, summary,
      recommendations and predicted_stars.
    - The exact same AI output is stored in submissions.json for the
      admin dashboard (no background refinement step).
    """
    submission_id = f"sub_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.randbelow(100)}"
    username = None

    try:
        pack = generate_ai_pack(payload.rating, payload.review_text, username=username)
    except Exception:
        # If Gemini is unavailable or errors, fall back to a simple template
        # so the request still succeeds.
        pack = _fallback_ai_pack(payload.rating, payload.review_text, username)

    submission = {
        "id": submission_id,
        "rating": payload.rating,
        "review_text": payload.review_text,
        "user_id": None,
        "username": username,
        "ai_response": pack.get("ai_response", "Thank you for your feedback."),
        "ai_summary": pack.get("ai_summary", "Feedback summary not available."),
        "ai_recommended_actions": pack.get("ai_recommended_actions", ""),
        "predicted_stars": pack.get("predicted_stars"),
        "prediction_explanation": pack.get("prediction_explanation", "AI prediction"),
        "timestamp": datetime.now().isoformat(),
        "status": "completed",
    }

    saved = save_submission(submission)
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to save submission")

    return SubmissionResponse(**submission)


@app.get("/api/submissions", response_model=List[AdminSubmission])
async def get_all_submissions(rating: Optional[int] = None, date: Optional[str] = None):
    """Get all submissions for admin dashboard with optional filters"""
    try:
        submissions = load_submissions()

        if DEBUG_REQUEST_LOGS:
            print(f"Loaded {len(submissions)} submissions from {DATA_FILE}")

        # Apply rating filter - STRICT filtering
        if rating is not None:
            filtered = []
            for s in submissions:
                # Ensure we compare integers
                sub_rating = s.get("rating")
                if isinstance(sub_rating, str):
                    sub_rating = int(sub_rating)
                if sub_rating == int(rating):
                    filtered.append(s)
            submissions = filtered
        
        # Apply date filter (format: YYYY-MM-DD)
        if date:
            submissions = [s for s in submissions if s.get("timestamp", "").startswith(date)]
        
        return [AdminSubmission(**sub) for sub in submissions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading submissions: {str(e)}")


@app.get("/api/submissions/{submission_id}", response_model=AdminSubmission)
async def get_submission(submission_id: str):
    """Get a single submission by id"""
    try:
        submissions = load_submissions()
        for s in submissions:
            if s.get("id") == submission_id:
                return AdminSubmission(**s)
        raise HTTPException(status_code=404, detail="Submission not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching submission: {str(e)}")


@app.get("/api/submission/{submission_id}", response_model=AdminSubmission)
async def get_submission_alias(submission_id: str):
    return await get_submission(submission_id=submission_id)


@app.get("/api/stats")
async def get_stats():
    """Get statistics for admin dashboard"""
    try:
        submissions = load_submissions()
        if not submissions:
            return {
                "total_reviews": 0,
                "average_rating": 0,
                "rating_distribution": {str(i): 0 for i in range(1, 6)}
            }

        ratings = [s["rating"] for s in submissions]
        total = len(ratings)
        avg = sum(ratings) / total if total > 0 else 0

        distribution = {str(i): ratings.count(i) for i in range(1, 6)}

        return {
            "total_reviews": total,
            "average_rating": round(avg, 2),
            "rating_distribution": distribution
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating stats: {str(e)}")


@app.get("/api/analytics")
async def get_analytics(
    date_range: Optional[str] = "all",
    rating: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get comprehensive analytics data for charts"""
    try:
        submissions = load_submissions()
        
        # Ensure submissions is a list
        if not isinstance(submissions, list):
            submissions = []
        
        # Apply filters
        filtered_submissions = submissions.copy()
        
        # Rating filter
        if rating is not None:
            filtered_submissions = [s for s in filtered_submissions if s.get("rating") == rating]
        
        # Date range filter with error handling
        if date_range != "all" or start_date or end_date:
            now = datetime.now()
            valid_submissions = []
            for s in filtered_submissions:
                try:
                    timestamp_str = s.get("timestamp", "")
                    if not timestamp_str:
                        continue
                    
                    # Try to parse timestamp
                    try:
                        if 'T' in timestamp_str:
                            # ISO format with time
                            sub_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        else:
                            # Date only format
                            sub_date = datetime.strptime(timestamp_str, "%Y-%m-%d")
                    except (ValueError, AttributeError):
                        # Skip invalid timestamps
                        continue
                    
                    if start_date and end_date:
                        # Custom date range
                        try:
                            cutoff = datetime.fromisoformat(start_date) if 'T' not in start_date else datetime.fromisoformat(start_date)
                            end_cutoff = datetime.fromisoformat(end_date) if 'T' not in end_date else datetime.fromisoformat(end_date)
                            if cutoff <= sub_date <= end_cutoff:
                                valid_submissions.append(s)
                        except (ValueError, AttributeError):
                            continue
                    elif date_range == "week":
                        cutoff = now - timedelta(days=7)
                        if sub_date >= cutoff:
                            valid_submissions.append(s)
                    elif date_range == "month":
                        cutoff = now - timedelta(days=30)
                        if sub_date >= cutoff:
                            valid_submissions.append(s)
                    elif date_range == "year":
                        cutoff = now - timedelta(days=365)
                        if sub_date >= cutoff:
                            valid_submissions.append(s)
                except Exception as e:
                    # Skip submissions with invalid timestamps
                    print(f"Warning: Skipping submission with invalid timestamp: {e}")
                    continue
            
            filtered_submissions = valid_submissions
        
        if not filtered_submissions:
            # Generate default trends for last 7 days even with no data
            trends_labels = []
            trends_data = []
            for i in range(6, -1, -1):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                trends_labels.append(date)
                trends_data.append(0)
            
            return {
                "total_reviews": 0,
                "average_rating": 0,
                "rating_distribution": {str(i): 0 for i in range(1, 6)},
                "trends_over_time": {"labels": trends_labels, "data": trends_data},
                "radar_analysis": {
                    "service_quality": 0,
                    "food_quality": 0,
                    "value_for_money": 0,
                    "ambience": 0,
                    "overall_satisfaction": 0,
                    "response_time": 0
                },
                "prediction_comparison": {"matches": 0, "ai_higher": 0, "ai_lower": 0},
                "positive_reviews": 0,
                "positive_percentage": 0,
                "ai_accuracy": None,
                "insights": ["No reviews found for the selected filters. Try adjusting your filters or submit more reviews."]
            }
        
        # Basic stats with error handling
        ratings = []
        for s in filtered_submissions:
            rating = s.get("rating")
            if rating is not None:
                try:
                    rating_int = int(rating)
                    if 1 <= rating_int <= 5:
                        ratings.append(rating_int)
                except (ValueError, TypeError):
                    continue
        
        total = len(ratings)
        avg = sum(ratings) / total if total > 0 else 0
        distribution = {str(i): ratings.count(i) for i in range(1, 6)}
        
        # Positive reviews (4-5 stars)
        positive = sum(1 for r in ratings if r >= 4)
        positive_pct = (positive / total * 100) if total > 0 else 0
        
        # Trends over time (last 7 days) with error handling
        trends_labels = []
        trends_data = []
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            count = 0
            for s in filtered_submissions:
                timestamp = s.get("timestamp", "")
                if timestamp and timestamp.startswith(date):
                    count += 1
            trends_labels.append(date)
            trends_data.append(count)
        
        # Radar analysis (simulated based on ratings)
        radar_analysis = {
            "service_quality": min(5, avg + 0.3),
            "food_quality": min(5, avg + 0.2),
            "value_for_money": min(5, avg - 0.1),
            "ambience": min(5, avg + 0.1),
            "overall_satisfaction": avg,
            "response_time": min(5, avg + 0.4)
        }
        
        # Prediction comparison - Compare user rating with AI predicted rating
        matches = 0
        ai_higher = 0
        ai_lower = 0
        total_with_prediction = 0
        
        for s in filtered_submissions:
            actual = s.get("rating")
            predicted = s.get("predicted_stars")
            # Ensure predicted is a valid integer between 1-5
            if predicted is not None and isinstance(predicted, (int, float)):
                predicted = int(predicted)
                if 1 <= predicted <= 5:
                    total_with_prediction += 1
                    if actual == predicted:
                        matches += 1
                    elif predicted > actual:
                        ai_higher += 1
                    else:
                        ai_lower += 1
        
        # Calculate AI accuracy: percentage of exact matches
        ai_accuracy = (matches / total_with_prediction * 100) if total_with_prediction > 0 else None
        
        # Generate insights with proper null checks
        insights = []
        if avg < 3:
            insights.append("⚠️ Average rating is below 3 stars. Immediate action required to improve customer satisfaction.")
        if positive_pct < 50:
            insights.append("📉 Less than 50% of reviews are positive. Focus on addressing common complaints.")
        if ai_accuracy is not None:
            if ai_accuracy > 80:
                insights.append("✅ AI prediction accuracy is excellent. The system is performing well.")
            elif ai_accuracy < 60:
                insights.append("⚠️ AI prediction accuracy needs improvement. Consider reviewing the prediction model.")
        if distribution.get('1', 0) > total * 0.2:
            insights.append("🚨 High number of 1-star reviews detected. Urgent intervention needed.")
        if len(trends_data) > 1 and trends_data[0] > 0 and trends_data[-1] > trends_data[0] * 1.5:
            insights.append("📈 Review volume is increasing. Great opportunity to gather more feedback.")
        
        return {
            "total_reviews": total,
            "average_rating": round(avg, 2),
            "rating_distribution": distribution,
            "trends_over_time": {
                "labels": trends_labels,
                "data": trends_data
            },
            "radar_analysis": radar_analysis,
            "prediction_comparison": {
                "matches": matches,
                "ai_higher": ai_higher,
                "ai_lower": ai_lower
            },
            "positive_reviews": positive,
            "positive_percentage": round(positive_pct, 1),
            "ai_accuracy": round(ai_accuracy, 1) if ai_accuracy is not None else None,
            "insights": insights if insights else ["No significant insights at this time."]
        }
    except Exception as e:
        print(f"Error generating analytics: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating analytics: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

