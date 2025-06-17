from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Any
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.errors import OAuthError

from app.services.auth_service import auth_service
from app.models.user_models import UserCreate, UserPublic
from app.db.models.user_model_db import User as UserDB
from app.models.token_models import TokenResponse # Removed TokenData, not explicitly used by router
from app.config.settings import settings
from app.db.redis_db import is_token_jti_valid, revoke_token_jti, revoke_all_user_tokens # Import Redis functions
from jose import JWTError, jwt
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

google_client = GoogleOAuth2(
    client_id=settings.GOOGLE_CLIENT_ID or "dummy_client_id",
    client_secret=settings.GOOGLE_CLIENT_SECRET or "dummy_client_secret",
)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    revoked_token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has been revoked",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        jti: str = payload.get("jti") # Extract JTI

        if user_id_str is None or jti is None:
            raise credentials_exception

        if not is_token_jti_valid(jti): # Check JTI validity in Redis
            raise revoked_token_exception

        try:
            uuid.UUID(user_id_str)
        except ValueError:
            raise credentials_exception

    except JWTError: # Covers decoding errors, signature errors, expiry
        raise credentials_exception

    user = auth_service.get_user_by_id(user_id=user_id_str)
    if user is None:
        raise credentials_exception

    # Attach jti to user object for logout route to access easily, if needed, or pass token itself
    # For simplicity, logout can re-decode or depend on a raw token accessor if preferred.
    # Here, we assume logout will also decode the token to get jti.
    return user

async def get_current_active_user(current_user: UserDB = Depends(get_current_user)) -> UserDB:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED) # Changed response_model
async def register_user_endpoint(user_in: UserCreate):
    try:
        user_db = auth_service.register_user(user_in)
        # Token creation and response for immediate login after registration
        access_token = auth_service.create_user_access_token(user=user_db)
        return TokenResponse(access_token=access_token, token_type="bearer", user=user_db.to_pydantic())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during registration.")


@router.post("/login", response_model=TokenResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth_service.authenticate_user(email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = auth_service.create_user_access_token(user=user)
    return TokenResponse(access_token=access_token, token_type="bearer", user=user.to_pydantic())

# Helper dependency to get raw token and jti for logout
async def get_token_jti_for_logout(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_exp": False}) # Allow expired for logout processing
        user_id_str: str = payload.get("sub")
        jti: str = payload.get("jti")
        if not user_id_str or not jti:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token for logout")
        return {"user_id": user_id_str, "jti": jti}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token for logout")


@router.post("/logout")
async def logout_endpoint(token_data: dict = Depends(get_token_jti_for_logout)):
    revoke_token_jti(jti=token_data["jti"], user_id=token_data["user_id"])
    return {"message": "Logout successful. Token has been revoked."}

@router.post("/logout-all")
async def logout_all_devices_endpoint(current_user: UserDB = Depends(get_current_active_user)):
    revoke_all_user_tokens(user_id=str(current_user.id))
    return {"message": "Logged out from all devices successfully."}


@router.get("/users/me", response_model=UserPublic)
async def read_users_me(current_user: UserDB = Depends(get_current_active_user)):
    return current_user.to_pydantic()

@router.get("/google")
async def auth_google(request: Request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET or not settings.GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google OAuth2 not configured.")
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    authorization_url = await google_client.get_authorization_url(
        redirect_uri, scope=["openid", "email", "profile"], extras_params={"access_type": "offline"}
    )
    return RedirectResponse(authorization_url)

@router.get("/google/callback", response_model=TokenResponse)
async def auth_google_callback(request: Request, code: str):
    # ... (Google callback logic remains largely the same, but token creation will use the new JTI mechanism)
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET or not settings.GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google OAuth2 not configured.")
    try:
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        token_data_google = await google_client.get_access_token(code, redirect_uri)
        user_info_google = await google_client.get_id_email(token_data_google["access_token"])

        user_email = user_info_google["email"]
        user_name = user_info_google.get("name", user_email.split('@')[0])
        profile_picture = user_info_google.get("picture", None)

        user_db_instance = auth_service.get_user_by_email(email=user_email)
        if not user_db_instance:
            user_create = UserCreate(
                email=user_email, name=user_name, profile_picture=profile_picture,
                password="dummy_password_for_oauth_user_" + code
            )
            try:
                user_db_instance = auth_service.register_user(user_create) # This now returns UserDB
            except ValueError as e: # Handles "Email already registered"
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to register OAuth user: {str(e)}")

        if not user_db_instance:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not login/register OAuth user.")

        access_token = auth_service.create_user_access_token(user=user_db_instance) # This now includes JTI handling
        return TokenResponse(access_token=access_token, token_type="bearer", user=user_db_instance.to_pydantic())

    except OAuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OAuth error: {e.error} - {e.description}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during Google authentication.")
