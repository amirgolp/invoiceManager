import redis
from app.config.settings import settings
import logging
from typing import Optional

# Global Redis client instance
redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True # Important for string operations
            )
            redis_client.ping() # Verify connection
            logging.info("Successfully connected to Redis.")
        except redis.exceptions.ConnectionError as e:
            logging.error(f"Could not connect to Redis: {e}")
            # Depending on strategy, might raise or handle to allow app start
            raise
    return redis_client

def close_redis_connection():
    global redis_client
    if redis_client:
        try:
            redis_client.close()
            logging.info("Successfully disconnected from Redis.")
        except Exception as e:
            logging.error(f"Error disconnecting from Redis: {e}")
        redis_client = None # Reset global client

# Token related functions
def store_token_jti(jti: str, user_id: str, expires_in_seconds: int):
    client = get_redis_client()
    # Store JTI with user_id for potential "logout all devices" later
    # Key: jti:{jti}, Value: user_id (or any simple placeholder like "valid")
    # Or more structured: user:{user_id}:jti:{jti}
    # For now, simple jti store:
    client.setex(f"jti:{jti}", expires_in_seconds, user_id)
    # Also maintain a list of active JTIs for a user for "logout all"
    client.sadd(f"user_jtis:{user_id}", f"jti:{jti}")
    client.expire(f"user_jtis:{user_id}", expires_in_seconds) # Keep user_jtis set expiry updated

def is_token_jti_valid(jti: str) -> bool:
    client = get_redis_client()
    return client.exists(f"jti:{jti}") == 1

def revoke_token_jti(jti: str, user_id: str):
    client = get_redis_client()
    client.delete(f"jti:{jti}")
    client.srem(f"user_jtis:{user_id}", f"jti:{jti}")

def revoke_all_user_tokens(user_id: str):
    client = get_redis_client()
    jti_keys = client.smembers(f"user_jtis:{user_id}")
    if jti_keys:
        # Prepare for pipeline if many keys
        pipe = client.pipeline()
        pipe.delete(*jti_keys) # Delete all individual jti entries
        pipe.delete(f"user_jtis:{user_id}") # Delete the set itself
        pipe.execute()
    logging.info(f"Revoked all tokens for user {user_id}. Keys affected: {jti_keys}")
