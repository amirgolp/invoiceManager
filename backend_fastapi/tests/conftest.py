import pytest
from fastapi.testclient import TestClient
import os
from mongoengine import connect as mongoengine_connect, disconnect as mongoengine_disconnect, get_connection, get_db
import redis

# Import your FastAPI app and settings AFTER potentially setting test env vars
# However, direct override of settings object is more reliable here.
from app.main import app
from app.config.settings import settings
# Import the actual client getter to be able to flush its DB or reconfigure it if needed
from app.db.redis_db import redis_client as global_redis_client_instance, close_redis_connection as app_close_redis_connection, get_redis_client as app_get_redis_client

TEST_MONGODB_NAME = "test_my_fastapi_db"
TEST_REDIS_DB_INT = 1 # Integer for Redis DB

@pytest.fixture(scope="session", autouse=True)
def override_settings_for_test_session():
    # This fixture runs once for the whole test session.
    original_mongo_db_name = settings.MONGODB_DB_NAME
    original_redis_db_int = settings.REDIS_DB
    original_mongo_uri = settings.MONGODB_URI # Assuming this might be just host/port

    # Override settings directly
    settings.MONGODB_DB_NAME = TEST_MONGODB_NAME
    settings.REDIS_DB = TEST_REDIS_DB_INT
    # If MONGODB_URI from .env includes a db name, it needs to be adjusted too, or ensure connect() overrides it.
    # The refined database.py/connect_to_mongo now explicitly uses settings.MONGODB_DB_NAME with connect(db=...).

    print(f"Session Start: Overriding settings for test. MONGODB_DB_NAME='{settings.MONGODB_DB_NAME}', REDIS_DB={settings.REDIS_DB}")

    # If Redis client was already initialized by app on import, try to close and reset it
    if global_redis_client_instance is not None:
        print("Closing pre-existing global Redis client for test session re-init.")
        app_close_redis_connection() # This sets global_redis_client_instance to None

    yield # Run all tests in the session

    # Restore original settings after the entire test session
    settings.MONGODB_DB_NAME = original_mongo_db_name
    settings.REDIS_DB = original_redis_db_int
    settings.MONGODB_URI = original_mongo_uri # Restore if it was changed
    print(f"Session End: Restored original settings. MONGODB_DB_NAME='{settings.MONGODB_DB_NAME}', REDIS_DB={settings.REDIS_DB}")

    # Clean up connections made during testing if any persist outside lifespan
    try:
        mongoengine_disconnect(alias='default')
    except Exception:
        pass
    if global_redis_client_instance is not None: # If TestClient lifespan didn't close it
        app_close_redis_connection()


@pytest.fixture(scope="function") # Changed from session to function for TestClient
def client(override_settings_for_test_session): # Depends on settings override
    # TestClient will trigger app lifespan: connect to (test) DBs on entry, disconnect on exit.
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function", autouse=True)
def setup_and_clear_test_dbs(override_settings_for_test_session): # Ensure settings are overridden
    # App lifespan (triggered by TestClient) should have connected to TEST_MONGODB_NAME and TEST_REDIS_DB_INT.
    # This fixture ensures the DBs are clean before each test function.

    # MongoDB Cleanup
    try:
        # Get the default connection established by the app's lifespan
        db_conn = get_connection()
        if db_conn.name != TEST_MONGODB_NAME:
            # This is a critical failure if occurs, means test isolation is broken.
            # Reconnecting here might be too late if app already used wrong DB.
            mongoengine_disconnect(alias='default') # Disconnect whatever it was
            mongoengine_connect(db=TEST_MONGODB_NAME, host=settings.MONGODB_URI, alias='default')
            db_conn = get_connection() # Get the new connection
            print(f"Reconnected to MongoDB for test: {db_conn.name}")

        # Clear all collections
        # print(f"MongoDB: Clearing all collections from test database '{db_conn.name}'...")
        for collection_name in db_conn.list_collection_names():
            # print(f"MongoDB: Dropping collection '{collection_name}'")
            db_conn.drop_collection(collection_name)
    except Exception as e:
        pytest.fail(f"Critical error during MongoDB test setup: {e}. Check MONGODB_URI and DB name settings for tests.")

    # Redis Cleanup
    try:
        # Get the Redis client established by the app's lifespan
        redis_test_client = app_get_redis_client() # This should use the overridden settings.REDIS_DB

        # Verify it's connected to the correct test DB
        # redis_info = redis_test_client.info() # Can get 'db0', 'db1' etc. from here
        # current_redis_db_num = int(redis_info[f'db{settings.REDIS_DB}']['keys']) # This is not how to get current DB
        # For redis-py, the db is part of connection_pool.connection_kwargs
        connected_redis_db = redis_test_client.connection_pool.connection_kwargs.get('db')
        if connected_redis_db != TEST_REDIS_DB_INT:
             pytest.fail(f"Redis client connected to DB {connected_redis_db}, expected {TEST_REDIS_DB_INT}. Test isolation broken.")

        # print(f"Redis: Flushing test database {settings.REDIS_DB}...")
        redis_test_client.flushdb()
    except Exception as e:
        pytest.fail(f"Critical error during Redis test setup: {e}. Check Redis connection and DB settings for tests.")

    yield # Run the test

    # Teardown (cleanup after test) is handled by flush at start of next test or session end.
