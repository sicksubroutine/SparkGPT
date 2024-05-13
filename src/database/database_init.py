from __future__ import annotations
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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
