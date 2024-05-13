from dataclasses import dataclass
from typing import override
from __init__ import db
from database.database_init import User
from utils.data_utils import time_get_unix
from utils.creds import hash_func


@dataclass
class CreateUser:
    username: str
    __password_hash: str
    __salt: str
    ip_address: str
    uuid: str
    user_agent: str
    identity_hash: str = ""
    sats: int = 0
    recently_paid: bool = False
    creation_date: str = time_get_unix()
    last_login: str = ""
    admin: bool = False
    user: User = None

    @override
    def __getattr__(self, item):
        try:
            if item == "_CreateUser__password_hash":
                raise AttributeError("Attribute is private")
            if item == "_CreateUser__salt":
                raise AttributeError("Attribute is private")
        except AttributeError as e:
            return None
        return self.__dict__[item]

    @override
    def __setattr__(self, key, value):
        if key == "_CreateUser__password_hash":
            raise AttributeError("Attribute is private")
        if key == "_CreateUser__salt":
            raise AttributeError("Attribute is private")
        self.__dict__[key] = value

    def __post_init__(self):
        identity_hash = hash_func(self.username, self.uuid, self.__salt)

        self.user = User(
            username=self.username,
            password_hash=self.__password_hash,
            salt=self.__salt,
            ip_address=self.ip_address,
            uuid=self.uuid,
            user_agent=self.user_agent,
            identity_hash=identity_hash,
            sats=self.sats,
            recently_paid=self.recently_paid,
            creation_date=self.creation_date,
            last_login=self.last_login,
            admin=self.admin,
        )
        self.__password_hash = None
        self.__salt = None
        db.session.add(self.user)
        db.session.commit()
