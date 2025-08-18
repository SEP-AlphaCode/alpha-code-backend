import os
from dotenv import load_dotenv

load_dotenv()  # load .env file

class Settings:
    TITLE = os.getenv("APP_TITLE", "My API")
    DESCRIPTION = os.getenv("APP_DESCRIPTION", "API description")
    VERSION = os.getenv("APP_VERSION", "0.0.1")
    CONTACT_NAME = os.getenv("APP_CONTACT_NAME", "")
    CONTACT_EMAIL = os.getenv("APP_CONTACT_EMAIL", "")
    LICENSE_NAME = os.getenv("APP_LICENSE_NAME", "")
    LICENSE_URL = os.getenv("APP_LICENSE_URL", "")

settings = Settings()
