from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from app.config import settings

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)

# Role access matrix mapping: Role -> Accessible Collections
ROLE_ACCESSIBLE_COLLECTIONS = {
    "doctor": ["clinical", "nursing", "general"],
    "nurse": ["nursing", "general"],
    "billing_executive": ["billing", "general"],
    "technician": ["equipment", "general"],
    "admin": ["clinical", "nursing", "billing", "equipment", "general"]
}

# Role access for SQL RAG
ROLE_SQL_RAG_ALLOWED = {
    "doctor": False,
    "nurse": False,
    "billing_executive": True,
    "technician": False,
    "admin": True
}

# Demo users DB
DEMO_USERS = {
    "dr.mehta": {"password": "doctor", "role": "doctor", "name": "Dr. Rajesh Mehta", "dept": "Clinical"},
    "nurse.priya": {"password": "nurse", "role": "nurse", "name": "Priya Sharma (RN)", "dept": "Nursing"},
    "billing.ravi": {"password": "billing_executive", "role": "billing_executive", "name": "Ravi Teja", "dept": "Billing"},
    "tech.anand": {"password": "technician", "role": "technician", "name": "Anand Verma", "dept": "Medical Equipment"},
    "admin.sys": {"password": "admin", "role": "admin", "name": "System Administrator", "dept": "Executive / IT"}
}

class TokenData(BaseModel):
    username: str
    role: str

class UserSession(BaseModel):
    username: str
    role: str
    name: str
    dept: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        return TokenData(username=username, role=role)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

def get_current_user_role(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_token(token).role
