from typing import Dict, Optional
from app.models.user_models import UserCreate, UserInDB, UserPublic
from app.utils.security import get_password_hash, verify_password, create_access_token
from datetime import timedelta

# In-memory store for users (replace with database interaction later)
fake_users_db: Dict[str, UserInDB] = {}

class AuthService:
    def register_user(self, user_create: UserCreate) -> UserInDB:
        if user_create.email in fake_users_db:
            # In a real app, this would raise an HTTPException
            # For now, let's assume controllers handle that based on return
            raise ValueError("Email already registered")

        hashed_password = get_password_hash(user_create.password)
        user_db = UserInDB(
            **user_create.model_dump(exclude={"password"}),
            hashed_password=hashed_password
        )
        fake_users_db[user_db.email] = user_db
        return user_db

    def authenticate_user(self, email: str, password: str) -> Optional[UserInDB]:
        user = fake_users_db.get(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def create_user_access_token(self, user: UserInDB, expires_delta_minutes: Optional[int] = None) -> str:
        expires_delta = None
        if expires_delta_minutes:
            expires_delta = timedelta(minutes=expires_delta_minutes)

        access_token = create_access_token(
            subject=user.email, expires_delta=expires_delta
        )
        return access_token

    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        return fake_users_db.get(email)

auth_service = AuthService()
