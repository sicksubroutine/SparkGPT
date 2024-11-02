import os
from pathlib import Path
from dotenv import load_dotenv

ENV_FILE = Path("../.env")

if not ENV_FILE.exists():
    print(" * Not loading .env file")
else:
    load_dotenv()
    print(" * Loading .env file")


from flask import Flask
from typing import Tuple
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy


def create_app() -> Tuple[Flask, SocketIO, SQLAlchemy]:
    from constants import DATABASE
    from database.database_init import (
        db,
        User,
        Conversation,
        ConversationHistory,
        Message,
        Payment,
    )

    database: SQLAlchemy = db

    app = Flask(
        "SparkGPT",
        static_url_path="/src/static",
        template_folder="/src/templates/",
    )
    app.secret_key = os.getenv("SESSIONKEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    database.init_app(app)

    with app.app_context():
        database.create_all()

    socketio = SocketIO(app)

    return app, socketio, database


app, socketio, db = create_app()
