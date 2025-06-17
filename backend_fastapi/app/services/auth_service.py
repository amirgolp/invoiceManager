from typing import Optional
from app.models.user_models import UserCreate, UserPublic # Pydantic models
from app.db.models.user_model_db import User as UserDB # MongoEngine User model
from app.utils.security import get_password_hash, verify_password, create_access_token
from datetime import timedelta, datetime # Ensure datetime is imported

class AuthService:
    def register_user(self, user_create: UserCreate) -> UserDB:
        # Check if user already exists
        existing_user = UserDB.objects(email=user_create.email).first()
        if existing_user:
            raise ValueError("Email already registered")

        hashed_password = get_password_hash(user_create.password)

        db_user = UserDB(
            email=user_create.email,
            name=user_create.name,
            profile_picture=user_create.profile_picture,
            is_active=user_create.is_active,
            # last_login will be updated on login
            # current_workspace_id is not set on registration directly through this model
            hashed_password=hashed_password
            # id, created_at, updated_at are handled by MongoEngine or model's save method
        )
        db_user.save() # This will also set created_at and updated_at
        return db_user

    def authenticate_user(self, email: str, password: str) -> Optional[UserDB]:
        user = UserDB.objects(email=email).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None

        # Optionally update last_login timestamp
        user.last_login = datetime.utcnow()
        user.save()
        return user

    def create_user_access_token(self, user: UserDB, expires_delta_minutes: Optional[int] = None) -> str:
        expires_delta = None
        if expires_delta_minutes:
            expires_delta = timedelta(minutes=expires_delta_minutes)

        access_token = create_access_token(
            subject=str(user.id), # Use user.id (UUID) as subject, converted to string
            expires_delta=expires_delta
        )
        return access_token

    def get_user_by_id(self, user_id: str) -> Optional[UserDB]: # Changed from email to ID for token sub
        try:
            return UserDB.objects(id=user_id).first()
        except Exception: # Handles invalid UUID format etc.
            return None

    # Keep get_user_by_email if needed elsewhere, e.g., for Google OAuth initial check
    def get_user_by_email(self, email: str) -> Optional[UserDB]:
        return UserDB.objects(email=email).first()

auth_service = AuthService()
