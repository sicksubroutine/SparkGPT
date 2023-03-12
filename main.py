from flask import Flask, render_template, session, request, redirect
import openai, os, markdown2
from tools import random_token, get_IP_Address, uuid_func
from replit import db

## TODO: Add more prompts.
## TODO: Design better account system.

TOKEN_LIMIT = 3000

users = db.prefix("user")
print(f"Number of Users: {len(users)}")
for user in users:
  print(db[user])
app = Flask(__name__, static_url_path='/static')

app.secret_key = os.environ['sessionKey']
secretKey = os.environ['gpt-API']
openai.api_key = f"{secretKey}"


def res(messages) -> str:
  response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                          messages=messages)
  assistant_response = response["choices"][0]["message"]["content"]
  token_usage = response["usage"]["total_tokens"]
  return assistant_response, token_usage


def token_check(messages) -> str:
  response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                          messages=messages)
  token_usage = response["usage"]["total_tokens"]
  return token_usage


def prompt_choose(prompt) -> str:

  prompt4chan = os.environ['4chanPrompt']
  IFSPrompt = os.environ['IFSPrompt']
  KetoPrompt = os.environ['KetoPrompt']
  PythonPrompt = os.environ['PythonPrompt']
  TherapistPrompt = os.environ['TherapistPrompt']
  foodMenuPrompt = os.environ['foodMenuPrompt']

  if prompt == 'prompt4chan':
    chosen_prompt = prompt4chan
    title = "4Chan AI"
  elif prompt == 'IFSPrompt':
    chosen_prompt = IFSPrompt
    title = "Internal Family Systems AI"
  elif prompt == 'KetoPrompt':
    chosen_prompt = KetoPrompt
    title = "Keto AI"
  elif prompt == 'PythonPrompt':
    chosen_prompt = PythonPrompt
    title = "Python AI"
  elif prompt == 'TherapistPrompt':
    chosen_prompt = TherapistPrompt
    title = "Therapist AI"
  elif prompt == 'foodMenu':
    chosen_prompt = foodMenuPrompt
    title = "Food Menu AI"
  else:
    chosen_prompt = None
    title = "I am Error"
  return chosen_prompt, title


@app.route("/", methods=["GET"])
def index():
  text = request.args.get("t")
  return render_template("index.html", text=text)


@app.route('/login', methods=['POST', 'GET'])
def login():
  ip_address = get_IP_Address(request)
  uuid = uuid_func()
  if request.method == 'POST':
    if 'prompt' in request.form:
      prompt = request.form.get('prompt')
      chosen_prompt, title = prompt_choose(prompt)
      session["title"] = title
      session["prompt"] = prompt
    elif 'custom_prompt' in request.form:
      chosen_prompt = request.form.get('custom_prompt')
      title = "Custom Prompt"
      session["title"] = title
      session["prompt"] = chosen_prompt
  if len(request.form) == 0:
    return redirect("/")
  else:
    if not session.get("username") or session.get("username") == None:
      users = db.prefix("user")
      for user in users:
        if db[user]["ip_address"] == ip_address and uuid == db[user]["uuid"]:
          session["username"] = db[user]["username"]
          session["ip_address"] = ip_address
          session[uuid] = db[user]["uuid"]
          return redirect("/chat")
      else:
        username = "user" + random_token()
        session["username"] = username
        session["ip_address"] = ip_address
        session["uuid"] = uuid
        db[username] = {
          "username": username,
          "ip_address": ip_address,
          "uuid": uuid,
          "messages": [{
            "role": "system",
            "content": chosen_prompt
          }]
        }
        return redirect("/chat")
    else:
      if session.get("username") and session.get("username") != None:
        username = session.get("username")
        db[username]["messages"] = [{
          "role": "system",
          "content": chosen_prompt
        }]
      return redirect("/chat")


@app.route("/chat", methods=["GET"])
def chat():
  print(session.get("username"))
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  msg = db[username]["messages"]

  messages = []
  for observed_dict in msg.value:
    messages.append(observed_dict.value)
  for message in messages:
    if message["role"] != "system":
      message["content"] = markdown2.markdown(message["content"],
                                              extras=["fenced-code-blocks"])
  return render_template("chat.html",
                         messages=messages,
                         title=session.get("title"))


@app.route("/respond", methods=["POST"])
def respond():
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  msg = db[username]["messages"]
  messages = []
  for observed_dict in msg.value:
    messages.append(observed_dict.value)
  if request.method == 'POST':
    message = request.form.get("message")
    messages.append({"role": "user", "content": message})
  response, token_usage = res(messages)
  if token_usage > TOKEN_LIMIT:
    oldest_assistant_message = next(
      (msg for msg in messages if msg["role"] == "assistant"), None)
    print(
      f"Token limit reached. Removing oldest assistant message: {oldest_assistant_message}"
    )
    if oldest_assistant_message:
      messages.remove(oldest_assistant_message)
  messages.append({"role": "assistant", "content": response})
  users = db.prefix("user")
  for user in users:
    if db[user]["username"] == session["username"]:
      db[user]["messages"] = messages
      break
  return redirect("/chat")


@app.route("/reset")
def reset_messages():
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  text = "Chat Reset"
  prompt = session.get("prompt")
  db[username]["messages"] = [{"role": "system", "content": f"{prompt}"}]
  session.pop("prompt", None)
  return redirect(f"/?t={text}")


@app.route("/logout")
def logout():
  session.pop("username", None)
  session.pop("ip_address", None)
  session.pop("title", None)
  session.pop("prompt", None)
  session.pip("uuid", None)
  return redirect("/")

app.run(host='0.0.0.0', port=81)
