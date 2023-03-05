from flask import Flask, render_template, session, request, redirect
import openai, os, markdown2
from tools import random_token, get_IP_Address
from replit import db

## TODO: Add ability to change between some preset prompts, "Therapist AI", "Python AI", and perhaps others?
## TODO: Improve look of the "chat" page.
## TODO: Improve structure of the various html pages.
## TODO: Randomly generate username on the backend and store it within the user's session.
## TODO: Get the user's IP address and associate it with their internal username.

app = Flask(__name__)

app.secret_key = os.environ['sessionKey']
secretKey = os.environ['gpt-API']
openai.api_key = f"{secretKey}"

prompt4chan = os.environ['4chanPrompt']
IFSPrompt = os.environ['IFSPrompt']
KetoPrompt = os.environ['KetoPrompt']
PythonPrompt = os.environ['PythonPrompt']
TherapistPrompt = os.environ['TherapistPrompt']

def res(messages):
  response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
  return response["choices"][0]["message"]["content"]

@app.route("/")
def index():
  return render_template("index.html")

@app.route('/login', methods=['POST', 'GET'])
def login():
  ip_address = get_IP_Address(request)
  if request.method == 'POST':
    prompt = request.form.get('prompt')
    if prompt == 'prompt4chan':
        chosen_prompt = prompt4chan
    elif prompt == 'IFSPrompt':
        chosen_prompt = IFSPrompt
    elif prompt == 'KetoPrompt':
        chosen_prompt = KetoPrompt
    elif prompt == 'PythonPrompt':
        chosen_prompt = PythonPrompt
    elif prompt == 'TherapistPrompt':
        chosen_prompt = TherapistPrompt
    else:
        chosen_prompt = None
  if len(request.form) == 0:
    return redirect("/")
  else:
    if not session.get("username"):
      form = request.form
      prompt = form.get("prompt")
      users = db.prefix("user")
      for user in users:
        if db[user]["ip_address"] == ip_address:
          session["username"] = db[user]["username"]
          session["ip_address"] = ip_address
      else:
        username = "user" + random_token()
        session["username"] = username
        session["ip_address"] = ip_address
        db[username] = {
          "username": username,
          "ip_address": ip_address,
          "messages": [{"role": "system", "content": f"{chosen_prompt}"}]
        }
    else:
      users = db.prefix("user")
      for user in users:
        if db[user]["ip_address"] == ip_address:
          session["ip_address"] = ip_address
      
  """else:
    form = request.form
    message = form.get("message")
    messages.append({"role": "user", "content": f"{message}"})
    response = res(messages)
    messages.append({"role": "assistant", "content": response})
    for message in messages:
        if message['role'] != 'system':
            message['content'] = markdown2.markdown(message['content'], extras=["fenced-code-blocks", "pygments"])
    return render_template('index.html', messages=messages)"""

@app.route("/chat")
def chat():
  if not session.get("username"):
    return redirect("/login")
  else:
    messages = []
    for message in db.prefix("user"):
      if db[message]["username"] == session["username"]:
        messages.append({"role": "user", "content": f"{message}"})
    response = res(messages)
    messages.append({"role": "assistant", "content": response})
    for message in messages:
      if message['role']!='system':
        pass
@app.route("/reset")
def reset_messages():
  global messages
  text = "Chat Reset"
  messages = []
  messages.append({"role": "system", "content": f"{prompt}"})
  return redirect(f"/?t={text}")

app.run(host='0.0.0.0', port=81)