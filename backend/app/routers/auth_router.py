from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from app.auth import DEMO_USERS, create_access_token

router = APIRouter(tags=["Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    dept: str

@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    username = credentials.username.strip().lower()
    password = credentials.password.strip()
    
    user_info = DEMO_USERS.get(username)
    if not user_info or user_info["password"] != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password. Available demo users: dr.mehta, nurse.priya, billing.ravi, tech.anand, admin.sys"
        )
        
    token = create_access_token(data={"sub": username, "role": user_info["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user_info["role"],
        "name": user_info["name"],
        "dept": user_info["dept"]
    }
