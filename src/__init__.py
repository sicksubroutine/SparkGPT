from flask import Flask
import os
from src.db_manage import DatabaseManager
from flask_socketio import SocketIO
from flask_seasurf import SeaSurf
from flask_sqlalchemy import SQLAlchemy
from constants import DATABASE, ENV_FILE

if not ENV_FILE.exists():
    print(" * Not loading .env file")
else:
    from dotenv import load_dotenv

    load_dotenv()
    print(" * Loading .env file")


app = Flask(__name__, static_url_path="/static")
app.secret_key = os.getenv("SESSIONKEY")
app.teardown_appcontext(DatabaseManager.close_db)
app.before_request(DatabaseManager.before_request)
csrf = SeaSurf()
csrf.init_app(app)
socketio = SocketIO(app)


app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
