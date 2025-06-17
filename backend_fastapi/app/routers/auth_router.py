from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Any
from httpx_oauth.clients.google import GoogleOAuth2 # Import GoogleOAuth2
from httpx_oauth.errors import OAuthError

from app.services.auth_service import auth_service, AuthService
from app.models.user_models import UserCreate, UserPublic, UserInDB
from app.models.token_models import TokenResponse, TokenData
from app.config.settings import settings
from jose import JWTError, jwt

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Initialize Google OAuth2 client
# Ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set in your environment or .env file
google_client = GoogleOAuth2(
    client_id=settings.GOOGLE_CLIENT_ID or "dummy_client_id", # Provide default if None
    client_secret=settings.GOOGLE_CLIENT_SECRET or "dummy_client_secret", # Provide default if None
    # scope=["openid", "email", "profile"], # Default scope
)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = auth_service.get_user_by_email(email=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user_endpoint(user_in: UserCreate): # Renamed to avoid conflict
    try:
        user_db = auth_service.register_user(user_in)
        return UserPublic(**user_db.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth_service.authenticate_user(email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth_service.create_user_access_token(user=user)
    user_public = UserPublic(**user.model_dump())
    return TokenResponse(access_token=access_token, token_type="bearer", user=user_public)

@router.post("/logout")
async def logout_endpoint(): # Renamed to avoid conflict
    return {"message": "Logout successful. Please delete your token."}

@router.get("/users/me", response_model=UserPublic)
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    return UserPublic(**current_user.model_dump())

# Google OAuth2 routes
@router.get("/google")
async def auth_google(request: Request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET or not settings.GOOGLE_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth2 not configured. Missing client ID, secret, or redirect URI."
        )
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    # Ensure redirect_uri is correctly formed if your app is behind a proxy or has a specific base URL
    # For example, using request.url_for might be more robust if base URL is configured in Uvicorn.
    # redirect_uri = request.url_for('auth_google_callback') # This requires route name to be set

    authorization_url = await google_client.get_authorization_url(
        redirect_uri,
        scope=["openid", "email", "profile"],
        extras_params={"access_type": "offline"}, # Optional: for refresh token
    )
    return RedirectResponse(authorization_url)

@router.get("/google/callback", response_model=TokenResponse)
async def auth_google_callback(request: Request, code: str):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET or not settings.GOOGLE_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth2 not configured."
        )
    try:
        # The redirect_uri must match exactly what was used in get_authorization_url
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        # redirect_uri = request.url_for('auth_google_callback') # if using url_for

        token_data_google = await google_client.get_access_token(code, redirect_uri)
        user_info_google = await google_client.get_id_email(token_data_google["access_token"])

        user_email = user_info_google["email"]
        user_name = user_info_google.get("name", user_email.split('@')[0]) # Use name if available, else part of email
        profile_picture = user_info_google.get("picture", None)

        user = auth_service.get_user_by_email(email=user_email)
        if not user:
            # User does not exist, create a new one
            # For OAuth users, password is not set directly or can be a long random string
            # They will always log in via Google.
            user_create = UserCreate(
                email=user_email,
                name=user_name,
                profile_picture=profile_picture,
                password="dummy_password_for_oauth_user_" + code # Ensure UserCreate has password field
            )
            try:
                user_db = auth_service.register_user(user_create) # This will hash the dummy password
                user = user_db # Use the newly created user
            except ValueError as e: # Already registered by some race condition? Unlikely with get_user_by_email check
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to register OAuth user: {str(e)}")

        elif user: # User exists, maybe update details
            # For now, we just use the existing user.
            # Later, add logic to update name/profile_picture if changed in Google.
            pass

        if not user: # Should not happen if logic above is correct
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not login/register OAuth user.")

        # Create an access token for our application
        access_token = auth_service.create_user_access_token(user=user)
        user_public = UserPublic(**user.model_dump())

        # Instead of returning TokenResponse directly, many apps redirect to a frontend URL with the token
        # e.g., return RedirectResponse(f"http://localhost:3000/auth/callback?token={access_token}")
        # For an API, returning the token directly is also common.
        return TokenResponse(access_token=access_token, token_type="bearer", user=user_public)

    except OAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {e.error} - {e.description}",
        )
    except Exception as e:
        # Log the exception for debugging
        print(f"Error during Google OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during Google authentication.",
        )
