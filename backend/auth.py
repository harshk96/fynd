"""
Authentication module for User and Admin panels - JSON-based storage
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import os
import json
from pathlib import Path

# Security setup
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# JSON file for user storage
USERS_FILE = Path(__file__).parent / "users.json"

# Ensure users file exists
if not USERS_FILE.exists():
    with open(USERS_FILE, "w") as f:
        json.dump([], f)

def load_users() -> list:
    """Load all users from JSON file"""
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading users: {e}")
        return []

def save_users(users: list):
    """Save users to JSON file"""
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def initialize_default_users():
    """Create default admin and user accounts if they don't exist"""
    users = load_users()
    
    # Default Admin Account
    admin_email = "admin@gmail.com"
    admin_exists = any(u.get("email") == admin_email for u in users)
    if not admin_exists:
        admin_user = {
            "username": "admin",
            "email": admin_email,
            "password": get_password_hash("Admin@123"),
            "role": "admin",
            "_id": "user_admin_default",
            "created_at": datetime.utcnow().isoformat()
        }
        users.append(admin_user)
        print("✅ Default admin account created: admin@gmail.com / Admin@123")
    
    # Default User Account
    user_email = "user@gmail.com"
    user_exists = any(u.get("email") == user_email for u in users)
    if not user_exists:
        user_account = {
            "username": "user",
            "email": user_email,
            "password": get_password_hash("User@123"),
            "role": "user",
            "_id": "user_user_default",
            "created_at": datetime.utcnow().isoformat()
        }
        users.append(user_account)
        print("✅ Default user account created: user@gmail.com / User@123")
    
    if not admin_exists or not user_exists:
        save_users(users)

def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email"""
    users = load_users()
    for user in users:
        if user.get("email") == email:
            return user
    return None

def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username"""
    users = load_users()
    for user in users:
        if user.get("username") == username:
            return user
    return None

def create_user(user_data: dict) -> dict:
    """Create a new user"""
    users = load_users()
    user_data["_id"] = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(users)}"
    user_data["created_at"] = datetime.utcnow().isoformat()
    users.append(user_data)
    save_users(users)
    return user_data

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_email(email)
    if user is None:
        raise credentials_exception
    
    # Remove password hash from user object
    user_copy = user.copy()
    user_copy.pop("password", None)
    return user_copy

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated admin user"""
    user = get_current_user(credentials)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    return user

# Initialize default users on module load
initialize_default_users()
