from flask import Flask, render_template, session, request, redirect, send_file
import openai, os, markdown2, random
from tools import random_token, get_IP_Address, uuid_func, hash_func, prompt_get
from replit import db

## TODO: Add more prompts.
## TODO: Be able to have different saved conversations.

TOKEN_LIMIT = 3000

users = db.prefix("user")
print(f"Number of Users: {len(users)}")

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
  return prompt_get(prompt)


@app.route("/", methods=["GET"])
def index():
  text = request.args.get("t")
  return render_template("index.html", text=text)


@app.route('/login', methods=['POST', 'GET'])
def login():
  ip_address = get_IP_Address(request)
  uuid = uuid_func()
  user_agent = request.headers.get('User-Agent')
  username = session.get('username')
  identity_hash = hash_func(ip_address, uuid, user_agent)
  if request.method == 'POST':
    if 'prompt' in request.form:
      prompt = request.form.get('prompt')
      prompt_dict = prompt_choose(prompt)
      chosen_prompt = prompt_dict["prompt"]
      title = prompt_dict["title"]
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
    if not username or username == None:
      users = db.prefix("user")
      for user in users:
        if identity_hash == db[user]["identity_hash"]:
          session["username"] = db[user]["username"]
          session["ip_address"] = ip_address
          session["uuid"] = uuid
          session["identity_hash"] = identity_hash
          session["user_agent"] = user_agent
          return redirect("/chat")
      else:
        username = "user" + random_token()
        session["username"] = username
        session["ip_address"] = ip_address
        session["uuid"] = uuid
        session["identity_hash"] = identity_hash
        db[username] = {
          "username": username,
          "ip_address": ip_address,
          "uuid": uuid,
          "user_agent": user_agent,
          "identity_hash": identity_hash,
          "messages": [{
            "role": "system",
            "content": chosen_prompt
          }]
        }
        return redirect("/chat")
    else:
      if session.get("username") and session.get(
          "username") != None and session.get("identity_hash") != None:
        username = session.get("username")
        db[username]["messages"] = [{
          "role": "system",
          "content": chosen_prompt
        }]
      return redirect("/chat")


@app.route("/chat", methods=["GET"])
def chat():
  if not session.get("username"):
    return redirect("/")
  text = request.args.get("t")
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
                         title=session.get("title"),
                         text=text)


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


@app.route("/export")
def export_messages():
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  messages = db[username]["messages"]
  markdown = ""
  for message in messages:
    if message['role'] == 'system':
      markdown += f"# {message['content']}\n\n"
    elif message['role'] == 'user':
      markdown += f"**User:** {message['content']}\n\n"
    elif message['role'] == 'assistant':
      markdown += f"**Assistant:** {message['content']}\n\n"
  random_num = random.randint(100000, 999999)
  filename = f"conversation_{random_num}.md"
  with open(filename, "w") as f:
    f.write(markdown)
  return send_file(filename, as_attachment=True)


@app.route("/logout")
def logout():
  session.pop("username", None)
  session.pop("ip_address", None)
  session.pop("title", None)
  session.pop("prompt", None)
  session.pop("uuid", None)
  session.pop("identity_hash", None)
  return redirect("/")


app.run(host='0.0.0.0', port=81)
