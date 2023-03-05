from flask import Flask, render_template, session, request, redirect
import openai, os, markdown2
from tools import random_token, get_IP_Address
from replit import db

## TODO: Add more prompts. 
## TODO: Account for 4096 token limit.

users = db.prefix("user")
print(f"Number of Users: {len(users)}")

app = Flask(__name__, static_url_path='/static')

app.secret_key = os.environ['sessionKey']
secretKey = os.environ['gpt-API']
openai.api_key = f"{secretKey}"

def res(messages) -> str:
  response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
  return response["choices"][0]["message"]["content"]

def prompt_choose(prompt) -> str:
  
  prompt4chan = os.environ['4chanPrompt']
  IFSPrompt = os.environ['IFSPrompt']
  KetoPrompt = os.environ['KetoPrompt']
  PythonPrompt = os.environ['PythonPrompt']
  TherapistPrompt = os.environ['TherapistPrompt']
  
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
  if request.method == 'POST':
    prompt = request.form.get('prompt')
    chosen_prompt, title = prompt_choose(prompt)
    session["title"] = title
    session["prompt"] = prompt
  if len(request.form) == 0:
    return redirect("/")
  else:
    if not session.get("username"):
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
          "messages": [{"role": "system", "content": chosen_prompt}]
        }
        return redirect("/chat")
    else:
      if session.get("username"):
        username = session.get("username")
        db[username]["messages"] = [{"role": "system", "content": chosen_prompt}]
      return redirect("/chat")


  

@app.route("/chat", methods=["GET"])
def chat():
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  msg = db[username]["messages"]

  messages = []
  for observed_dict in msg.value:
    messages.append(observed_dict.value)
  for message in messages:
    if message["role"]!="system":
      message["content"] = markdown2.markdown(message["content"], extras=["fenced-code-blocks"])
  return render_template("chat.html", messages=messages, title=session.get("title"))

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
  response = res(messages)
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

app.run(host='0.0.0.0', port=81)