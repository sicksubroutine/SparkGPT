from requests import Request
import random
import string
import hashlib
import uuid
import logging
from logging import Logger
from utils.data_utils import time_get
from flask import request as flask_request

logger: Logger = logging.getLogger(__name__)


def get_ip_address(request: Request) -> str:
    """Retrieves the IP address of the user.

    :param request flask_request: The request object.
    :return str: The IP address of the user.
    """
    try:
        return request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    except Exception as e:
        logger.error(f"Failed to get IP Address: {e}")
        return None


def uuid_func() -> str:
    """Generates a UUID or device_ID.

    :return str: A UUID or device_ID.
    """
    return f"{uuid.uuid1()}"


def hash_func(*args: tuple) -> str:
    """Generates a hash based on the given arguments.

    Args:
      *args (str): The arguments to be hashed.

    Returns:
      str: A hash.

    Notes:
      - The arguments are concatenated and hashed using the SHA256 algorithm.
      - The hash is returned as a hexadecimal string.
    """
    return hashlib.sha256("".join(args).encode()).hexdigest()


def salt_get() -> str:
    """
    Generate a random salt consisting of uppercase letters, lowercase letters,
    digits, and punctuation. The salt is 30 characters long.

    Returns:
    str: A random salt.
    """

    return "".join(
        random.choice(string.ascii_letters + string.digits + string.punctuation)
        for _ in range(30)
    )


class Credentials:
    def __init__(self, request):
        self.request = request
        self.headers: dict = request.headers
        self.form: dict[str, str] = request.form
        self.user_agent = self.headers.get("User-Agent")
        self.uuid = uuid_func()
        self.ip_address = get_ip_address(request)

    def login_current_user(self):
        try:
            self.username = self.form["username"].lower()
            password = self.form["password"]
            db_user = self.database.get_user(self.username)
            if db_user is None:
                return {"error": "User does not exist."}
            password_hash = hash_func(password, db_user["salt"])
            if password_hash != db_user["password"]:
                return {"error": "Incorrect password."}
            return {"success": "User logged in."}

        except Exception as e:
            logger.error(f"Failed to get username: {e}")
            return {"error": "Failed to get username."}

    def create_new_user(self):
        try:
            self.username = self.form["username"].lower()
            db_user = self.database.get_user(self.username)
            if db_user is not None:
                return {"error": "User already exists."}
            password = self.form["password"]
            password_confirm = self.form["password_confirm"]
            if password != password_confirm:
                return {"error": "Passwords do not match."}
            salt = salt_get()
            password_hash = hash_func(password, salt)
            identity_hash = hash_func(self.username, self.uuid)

            self.database.insert_user(
                username=self.username,
                password=password_hash,
                salt=salt,
                ip_address=self.ip_address,
                uuid=self.uuid,
                user_agent=self.user_agent,
                identity_hash=identity_hash,
                sats=0,
                recently_paid=False,
                creation_date=time_get(),
            )
            return {"success": "User created."}

        except Exception as e:
            logger.error(f"Failed to get username: {e}")
            return {"error": "Failed to get username."}
