from __future__ import annotations
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from __init__ import db
from dataclasses import dataclass
from typing import override


@dataclass
class CreateUser:
    username: str
    __password_hash: str
    __salt: str
    ip_address: str
    uuid: str
    user_agent: str
    identity_hash: str
    sats: int = 0
    recently_paid: bool = False
    creation_date: str = ""
    last_login: str = ""
    admin: bool = False

    user: User

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
        self.user = User(
            username=self.username,
            password_hash=self.__password_hash,
            salt=self.__salt,
            ip_address=self.ip_address,
            uuid=self.uuid,
            user_agent=self.user_agent,
            identity_hash=self.identity_hash,
            sats=self.sats,
            recently_paid=self.recently_paid,
            creation_date=self.creation_date,
            last_login=self.last_login,
            admin=self.admin,
        )
        self.password = None
        self.salt = None
        db.session.add(self.user)
        db.session.commit()


class CreateConversation:
    username: str
    model: str
    title: str
    prompt: str
    summary: str = ""
    short_summary: str = ""

    conversation: Conversation

    def __post_init__(self):
        self.conversation = Conversation(
            username=self.username,
            model=self.model,
            title=self.title,
            prompt=self.prompt,
            summary=self.summary,
            short_summary=self.short_summary,
        )
        db.session.add(self.conversation)
        db.session.commit()


class User(db.Model):
    username = db.Column(db.String, primary_key=True)
    password_hash = db.Column(db.String)
    salt = db.Column(db.String)
    ip_address = db.Column(db.String)
    uuid = db.Column(db.String)
    user_agent = db.Column(db.String)
    identity_hash = db.Column(db.String)
    sats = db.Column(db.Integer)
    recently_paid = db.Column(db.Boolean)
    creation_date = db.Column(db.String)
    last_login = db.Column(db.String, default="")
    admin = db.Column(db.Boolean, default=False)


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, db.ForeignKey("user.username"))
    model = db.Column(db.String)
    title = db.Column(db.String)
    prompt = db.Column(db.String)
    summary = db.Column(db.String, default="")
    short_summary = db.Column(db.String, default="")


class ConversationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"))
    role = db.Column(db.String)
    content = db.Column(db.String)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"))
    role = db.Column(db.String)
    content = db.Column(db.String)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, db.ForeignKey("user.username"))
    amount = db.Column(db.Integer)
    memo = db.Column(db.String)
    payment_request = db.Column(db.String)
    payment_hash = db.Column(db.String)
    invoice_status = db.Column(db.String)
