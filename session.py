from db_manage import DatabaseManager
from various_tools import time_get
from creds import Credentials


class SessionHandler:
    def __init__(self, session: dict, database: DatabaseManager, creds: Credentials):
        self.session = session
        self.database = database
        self.creds = creds
        self.username = creds.username
        self.ip_address = creds.ip_address
        self.uuid = creds.uuid
        self.user = database.get_user(self.username)

    def do_the_things(self):
        if self.user is None:
            return {"error": "User does not exist."}
        self.update_session()
        self.update_user_time()
        self.handle_admin()
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
