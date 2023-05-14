from flask import Flask
import os
from db_manage import close_db, before_request

def create_app():
    app = Flask(__name__, static_url_path='/static')
    app.secret_key = os.environ['SESSIONKEY']
    app.teardown_appcontext(close_db)
    app.before_request(before_request)
    return app