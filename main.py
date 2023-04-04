from flask import Flask, render_template, session, request, redirect, send_file, jsonify
import os, markdown2
from tools import random_token, get_IP_Address, uuid_func, hash_func, prompt_get, check_old_markdown, res
from replit import db


## TODO: Add more prompts.
## TODO: Make the front page look better.

## TODO: Consider adding Lightning Network payments.
## TODO: Consider adding a way to login with the Lightning Network.
##TODO: Add ability to change AI models.

TOKEN_LIMIT = 3000

users = db.prefix("user")
"""print(f"Number of Users: {len(users)}")
for user in users:
  print(db[user])"""

app = Flask(__name__, static_url_path='/static')
app.secret_key = os.environ['sessionKey']


def prompt_choose(prompt) -> str:
  return prompt_get(prompt)


@app.route("/", methods=["GET"])
def index():
  text = request.args.get("t")
  conv = []
  if session.get("username") and session.get("identity_hash"):
    username = session["username"]
    conv = db[username]["conversations"]
  return render_template("index.html", text=text, conversations=conv)

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
      prompt = "CustomPrompt"
      chosen_prompt = request.form.get('custom_prompt')
      title = "Custom Prompt"
      session["title"] = title
      session["prompt"] = chosen_prompt
  elif 'conversation' in request.args:
    conversation = request.args.get('conversation')
    session["conversation"] = conversation
    prompt = db[username]["conversations"][conversation]["prompt"]
    prompt_dict = prompt_choose(prompt)
    title = prompt_dict["title"]
    session["title"] = title
    return redirect("/chat")
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
        conversation = "conversation" + random_token()
        session["conversation"] = conversation
        db[username] = {
          "username": username,
          "ip_address": ip_address,
          "uuid": uuid,
          "user_agent": user_agent,
          "identity_hash": identity_hash,
          "conversations": {
            conversation: {
              "prompt": prompt,
              "conversation_history": [{
              "role": "system",
              "content": chosen_prompt
              }],
              "messages": [{
                "role": "system",
                "content": chosen_prompt
              }]
            }
          }
        }
        return redirect("/chat")
    else:
      if session.get("username") and session.get("identity_hash"):
        username = session.get("username")
        conversation = "conversation" + random_token()
        session["conversation"] = conversation
        db[username]["conversations"][conversation] = {
          "prompt": prompt,
          "conversation_history": [{
            "role": "system",
            "content": chosen_prompt
          }],
          "messages": [{
            "role": "system",
            "content": chosen_prompt
          }]
        }
      return redirect("/chat")


@app.route("/chat", methods=["GET"])
def chat():
  if not session.get("username"):
    return redirect("/")
  text = request.args.get("t")
  username = session["username"]
  conversation = session["conversation"]
  msg = db[username]["conversations"][conversation]["conversation_history"]
  if db.get(username, {}).get("conversations", {}).get(
      conversation, {}).get("summary") is None and len(msg) > 1:
    long_res, short_res = summary_of_messages()
    db[username]["conversations"][conversation]["summary"] = long_res
    db[username]["conversations"][conversation]["short_summary"] = short_res
  messages = []
  for observed_dict in msg.value:
    messages.append(observed_dict.value)
  for message in messages:
    if message["role"] != "system":
      message["content"] = markdown2.markdown(message["content"],
                                              extras=["fenced-code-blocks"])
  for index, message in enumerate(messages):
    message["index"] = index
  return render_template("chat.html",
                         messages=messages,
                         title=session.get("title"),
                         text=text)


@app.route("/respond", methods=["POST"])
def respond():
  if not session.get("username"):
    return redirect("/")
  messages = []
  username = session["username"]
  conversation = session["conversation"]
  msg = db[username]["conversations"][conversation]["messages"]
  if db[username]["conversations"][conversation]["conversation_history"] is None:
    conversation_history = []
  else:
    conversation_history = db[username]["conversations"][conversation]["conversation_history"]
  for observed_dict in msg.value:
    messages.append(observed_dict.value)
    if observed_dict in conversation_history:
      continue
    else:
      conversation_history.append(observed_dict)
  if request.method == 'POST':
    message = request.form.get("message")
    messages.append({"role": "user", "content": message})
    if not message in conversation_history:
      conversation_history.append({"role": "user", "content": message})
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
  if not response in conversation_history:
      conversation_history.append({"role": "assistant", "content": response})
  users = db.prefix("user")
  for user in users:
    if db[user]["username"] == session["username"]:
      db[user]["conversations"][conversation]["conversation_history"] = conversation_history
      print(f"{user}'s conversation history size is now: {len(conversation_history)}")
      print(f"{user}'s message size is now: {len(messages)}")
      db[user]["conversations"][conversation]["messages"] = messages
      break
  return jsonify({"response": response})


@app.route("/reset")
def reset_messages():
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  text = "Chat Reset!"
  prompt = session.get("prompt")
  conversation = session["conversation"]
  db[username]["conversations"][conversation]["messages"] = [{
    "role":
    "system",
    "content":
    f"{prompt}"
  }]
  db[username]["conversations"][conversation].pop("summary")
  db[username]["conversations"][conversation].pop("short_summary")
  print("summary removed")
  session.pop("prompt", None)
  session
  return redirect(f"/?t={text}")


@app.route("/delete_convo", methods=["GET"])
def delete_convo():
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  conversation = request.args["conversation"]
  db[username]["conversations"].pop(conversation)
  return redirect("/")


@app.route("/delete_msg", methods=["GET"])
def delete_msg():
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  conversation = session["conversation"]
  msg_index = int(request.args["msg"])
  try:
    """for i in range(len(db[username]["conversations"][conversation]["messages"])-1, msg_index-1, -1):
      print(i)"""
    del db[username]["conversations"][conversation]["messages"][msg_index]
    del db[username]["conversations"][conversation]["conversation_history"][msg_index]
    return redirect("/chat")
  except Exception as e:
    print(e)
    return redirect("/chat")


def summary_of_messages():
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  conversation = session["conversation"]
  messages = db[username]["conversations"][conversation]["messages"]
  summary_msgs = ""
  for index, message in enumerate(messages):
    if message["role"] == "user":
      if index > 1:
        break
      summary_msgs += message["content"]
    elif message["role"] == "assistant":
      pass
  prompt = "The user's question or request should be summerized into five words or less. No explanation or elaboration. Response needs to be five words or less, no puncutation."
  arr = [{
    "role": "system",
    "content": f"{prompt}"
  }, {
    "role": "user",
    "content": summary_msgs
  }]
  response, tokens = res(arr)
  longer_response = response
  response = response.split()
  response = "_".join(response)
  response = response.replace(".", "")
  response = response.replace(",", "")
  return longer_response, response


@app.route("/export")
def export_messages():
  if not session.get("username"):
    return redirect("/")

  check_old_markdown()
  username = session["username"]
  conversation = session["conversation"]
  messages = db[username]["conversations"][conversation]["conversation_history"]
  summary = db[username]["conversations"][conversation]["short_summary"]
  markdown = ""
  for message in messages:
    if message['role'] == 'system':
      markdown += f"# {message['content']}\n\n"
    elif message['role'] == 'user':
      markdown += f"**User:** {message['content']}\n\n"
    elif message['role'] == 'assistant':
      markdown += f"**Assistant:** {message['content']}\n\n"
  filename = f"{summary}.md"
  path = "static/markdown/"
  path_filename = path + filename

  with open(path_filename, "w") as f:
    f.write(markdown)
  return send_file(path_filename, as_attachment=True)


@app.route("/logout")
def logout():
  session.pop("username", None)
  session.pop("ip_address", None)
  session.pop("title", None)
  session.pop("prompt", None)
  session.pop("uuid", None)
  session.pop("identity_hash", None)
  session.pop("conversation", None)
  return redirect("/")


app.run(host='0.0.0.0', port=81)
