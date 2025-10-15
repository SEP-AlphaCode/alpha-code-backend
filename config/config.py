import os
from dotenv import load_dotenv
from aiocache import caches

load_dotenv()  # load .env file

class Settings:
    TITLE = os.getenv("APP_TITLE", "My API")
    DESCRIPTION = os.getenv("APP_DESCRIPTION", "API description")
    VERSION = os.getenv("APP_VERSION", "0.0.1")
    CONTACT_NAME = os.getenv("APP_CONTACT_NAME", "")
    CONTACT_EMAIL = os.getenv("APP_CONTACT_EMAIL", "")
    LICENSE_NAME = os.getenv("APP_LICENSE_NAME", "")
    LICENSE_URL = os.getenv("APP_LICENSE_URL", "")

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

settings = Settings()

caches.set_config({
    "default": {
        "cache": "aiocache.RedisCache",
        "endpoint": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "password": settings.REDIS_PASSWORD,
        "timeout": 5,
        "serializer": {
            "class": "aiocache.serializers.JsonSerializer"
        }
    }
})