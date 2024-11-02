from sparkgpt.db_manage import DatabaseManager
from utils.data_utils import time_get
from sparkgpt.utils.creds import Credentials
from dataclasses import dataclass, field


@dataclass(slots=True)
class SessionHandler:
    session: dict
    database: DatabaseManager
    creds: Credentials
    username: str = field(default="")
    ip_address: str = field(default="")
    uuid: str = field(default="")
    user: dict = field(default=None)

    def __post_init__(self):
        self.user = self.database.get_user(self.username)

    def do_the_things(self):
        try:
            if self.user is None:
                return {"error": "User does not exist."}
            self.update_session()
            self.update_user_time()
            self.handle_admin()
        except Exception as e:
            return {"error": f"Failed to update session: {e}"}
        return {"success": "Session updated."}

    def update_session(self):
        self.session["username"] = self.username
        self.session["ip_address"] = self.ip_address
        self.session["uuid"] = self.uuid
        self.session["force_buy"] = False
        self.session["identity_hash"] = self.user["identity_hash"]

    def update_user_time(self):
        self.database.update_user(self.session["username"], "last_login", time_get())

    def handle_admin(self):
        if self.user["admin"]:
            self.session["admin"] = True
        else:
            self.session["admin"] = False
