from __init__ import app, socketio
from flask import Flask
from flask_socketio import SocketIO
import sys

# from database.user_handler import CreateUser

# from utils.creds import (
#     Credentials,
#     hash_func,
#     salt_get,
#     uuid_func,
#     get_ip_address,
#     uuid_func,
# )

app: Flask = app
socketio: SocketIO = socketio


@app.route("/")
def index():

    # username = "test"
    # password = "password"
    # salt = salt_get()
    # password_hash = hash_func(password, salt)
    # password = None
    # ip_address = get_ip_address()
    # uuid = uuid_func()
    # date = time_get()
    # user_agent = "test"
    # identity_hash = hash_func(username, uuid, salt)

    # user = CreateUser(
    #     username, password_hash, salt, ip_address, uuid, user_agent, identity_hash
    # )

    return "Hello, World!"


if __name__ == "__main__":
    try:
        socketio.run(app, host="0.0.0.0", port=81)
    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit()
