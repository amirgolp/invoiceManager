from mongoengine import connect, disconnect, get_connection
from app.config.settings import settings
import logging

def connect_to_mongo():
    try:
        # Construct URI without DB name if MONGODB_DB_NAME is to be used explicitly
        # Assuming MONGODB_URI might be like "mongodb://localhost:27017" or "mongodb://localhost:27017/actual_db"
        # If MONGODB_URI already contains a DB name, MongoEngine's `db` param will override it for that connection.

        # MongoEngine's connect function allows specifying the 'db' name separately,
        # which will override any db name in the host URI string for that specific connection.
        # It also allows connecting to multiple databases using aliases.
        # For simplicity, we'll rely on the 'db' parameter for the default connection.

        print(f"Connecting to MongoDB - Host: {settings.MONGODB_URI}, DB: {settings.MONGODB_DB_NAME}")
        connect(
            db=settings.MONGODB_DB_NAME,
            host=settings.MONGODB_URI, # This URI can be just the server address or include a default DB
            alias='default' # Explicitly use the default alias
        )

        # Verify connection by trying to get server info from the correct DB
        conn = get_connection()
        conn.admin.command('ping') # Ping the server
        logging.info(f"Successfully connected to MongoDB. DB Name: {conn.name}")

    except Exception as e:
        logging.error(f"Could not connect to MongoDB (DB: {settings.MONGODB_DB_NAME}, URI: {settings.MONGODB_URI}): {e}")
        raise

def close_mongo_connection():
    try:
        disconnect(alias='default') # Disconnect the default alias
        logging.info("Successfully disconnected from MongoDB.")
    except Exception as e:
        logging.error(f"Error disconnecting from MongoDB: {e}")
