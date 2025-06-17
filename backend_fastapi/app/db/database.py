from mongoengine import connect, disconnect
from app.config.settings import settings
import logging

def connect_to_mongo():
    try:
        connect(host=settings.MONGODB_URI)
        logging.info("Successfully connected to MongoDB.")
    except Exception as e:
        logging.error(f"Could not connect to MongoDB: {e}")
        # Depending on the strategy, you might want to raise the exception
        # or handle it to allow the app to start for certain non-DB-dependent endpoints.
        raise

def close_mongo_connection():
    try:
        disconnect()
        logging.info("Successfully disconnected from MongoDB.")
    except Exception as e:
        logging.error(f"Error disconnecting from MongoDB: {e}")
