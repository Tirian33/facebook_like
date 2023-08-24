from os import environ

from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URI = environ.get("SQLALCHEMY_DATABASE_URI")
SQLALCHEMY_SESSION_TIMEOUT = int(environ.get("SQLALCHEMY_SESSION_TIMEOUT"))
SECRET_KEY = 'Temp Holding Key'