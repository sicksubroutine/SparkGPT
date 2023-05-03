from flask import Flask, render_template, session, request, redirect, send_file, jsonify, Response, g
from flask_socketio import SocketIO
import os, markdown2, requests, qrcode, random, logging, sqlite3
from tools import random_token, get_IP_Address, uuid_func, hash_func, prompt_get, check_old_markdown, res, get_bitcoin_cost, estimate_tokens
from db_manage import DatabaseManager
from replit import db

logging.basicConfig(filename='logfile.log', level=logging.error)

## TODO: Add more prompts.
## TODO: Make the front page look better.
## TODO: Make the chat app look better across different interfaces.
## TODO: Consider adding a way to login with the Lightning Network.
## LNURL-AUTH : https://github.com/lnurl/luds/blob/luds/04.md
## TODO: Add ability to change AI models.
## TODO: Move away from Replit database and use sqllite. ALMOST DONE YOU FUCK!

API_KEY = os.environ['lnbits_api']
URL = "https://legend.lnbits.com/api/v1/payments/"
HEADERS = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}
TOKEN_LIMIT = 3000

app = Flask(__name__, static_url_path='/static')
app.secret_key = os.environ['sessionKey']
socketio = SocketIO(app)

DATABASE = "prime_database.db"

users = db.prefix("user")
logging.info(f"Number of Users: {len(users)}")


"""for user in users:
  del db[user]"""

def open_db():
    if 'database' not in g:
        g.database = sqlite3.connect(DATABASE)
        g.database.row_factory = sqlite3.Row
    return g.database

@app.teardown_appcontext
def close_db(error):
    if 'database' in g:
        g.database.close()

@app.before_request
def before_request():
    g.d_base = DatabaseManager(open_db)


@app.route("/", methods=["GET"])
def index():
  text = request.args.get("t")
  conv = {}
  if session.get("username") and session.get("identity_hash"):
    username = session["username"]
    """d_base = g.d_base
    convo = d_base.get_conversations_for_user(username)
    conv = {}
    conv = {
    c['id']: {
      'prompt': c['prompt'],
      'summary': c['summary']
      }
      for c in convo
    }
    print(f"Printing conv in index route: {conv}")  """
    conv = db[username]["conversations"]
  return render_template("index.html", text=text, conversations=conv)


def clean_up_invoices():
  path = "static/qr/"
  for filename in os.listdir(path):
    if filename.endswith(".png"):
      os.remove(path + filename)


@app.route('/get_invoice', methods=['GET'])
def get_invoice():
  sats = request.args.get('sats')
  memo = f"Payment for {sats} Sats"
  data = {
    "out": False,
    "amount": sats,
    "memo": memo,
    "expiry": 1500,
    "webhook": "https://ChatGPT-Flask-App.thechaz.repl.co/webhook"
  }
  res = requests.post(URL, headers=HEADERS, json=data)
  if res.ok:
    session.pop("payment_request", None)
    session.pop("payment_hash", None)
    invoice = res.json()
    payment_request = invoice.get("payment_request")
    payment_hash = invoice.get("payment_hash")
    username = session.get("username")
    d_base = g.d_base
    d_base.insert_payment(username=username,
                          amount=sats,
                          memo=memo,
                          payment_request=payment_request,
                          payment_hash=payment_hash,
                          invoice_status='not paid')
    session["payment_request"] = payment_request
    session["payment_hash"] = payment_hash
    return {"status": "success", "payment_request": payment_request}
  else:
    logging.error("Error:", res.status_code, res.reason)


@app.route("/qrcode_gen", methods=['GET'])
def qrcode_gen():
  payment_request = request.args.get('payment_request')
  qr_code = qrcode.make(f"lightning:{payment_request}")
  random_filename = "qrcode_" + str(random.randint(0, 1000000)) + ".png"
  path = (f"static/qr/{random_filename}")
  if not os.path.exists("static/qr/"):
    os.makedirs("static/qr/")
  qr_code.save(f"static/qr/{random_filename}")
  return path


def payment_check(payment_hash):
  url = f"{URL}{payment_hash}"
  response = requests.get(url, headers=HEADERS)
  data = response.json()
  if response.ok:
    paid = data.get("paid")
    return paid
  else:
    logging.error("Error:", response.status_code, response.reason)


@app.route("/webhook", methods=["POST"])
def webhook():
  d_base = g.d_base
  data = request.json
  payment_hash = data.get("payment_hash")
  paid = payment_check(payment_hash)
  if paid:
    d_base.update_payment(payment_hash, "invoice_status", "paid")
    text = f"{payment_hash} has been paid!"
    logging.info(text)
    payment = d_base.get_payment(payment_hash)
    sats = payment["amount"]
    username = payment["username"]
    current_user = d_base.get_user(username)
    current_balance = current_user["sats"]
    print(f"Current balance before sats: {current_balance}")
    current_balance += sats
    d_base.update_user(username, "sats", current_balance)
    d_base.update_user(username, "recently_paid", True)
    current_user = d_base.get_user(username)
    print(f"Current balance after sats: {current_user['sats']}")
    ##################################################
    db[username]["sats"] += sats
    db[username]["recently_paid"] = True
    ##################################################
    clean_up_invoices()
  return "OK"


@app.route('/payment_updates')
def payment_updates():
  payment_hash = session["payment_hash"]
  d_base = g.d_base
  invoice_status = d_base.get_invoice_status(payment_hash)
  if invoice_status == 'paid':
    data = 'data: {"status": "paid"}\n\n'
  else:
    data = 'data: {"status": "not paid"}\n\n'
  return Response(data, content_type='text/event-stream')


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
      prompt_dict = prompt_get(prompt)
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
    # TODO: add conversation to database
    """d_base = g.d_base
    convo = d_base.get_conversation(conversation)"""
    prompt = db[username]["conversations"][conversation]["prompt"]
    if prompt != "CustomPrompt":
      prompt_dict = prompt_get(prompt)
      title = prompt_dict["title"]
      session["title"] = title
    else:
      title = "Custom Prompt AI"
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
        d_base = g.d_base
        d_base.insert_user(username, ip_address, uuid, user_agent, identity_hash)
        convo = d_base.insert_conversation(username, prompt, chosen_prompt)
        logging.info(f"New conversation: {convo}")
        session["convo"] = convo["conversation_id"]
        logging.info(f"New conversation: {convo['conversation_id']}")
        db[username] = {
          "username": username,
          "ip_address": ip_address,
          "uuid": uuid,
          "user_agent": user_agent,
          "identity_hash": identity_hash,
          "sats": 0,
          "recently_paid": False,
          "conversations": {
            conversation: {
              "prompt":
              prompt,
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
        conversation = "conversation" + random_token()
        session["conversation"] = conversation
        d_base = g.d_base
        convo = d_base.insert_conversation(username, prompt, chosen_prompt)
        session["convo"] = convo["conversation_id"]
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
  # TODO: pull the user from database
  # TODO: pull conversations from database using username, pull conversation history
  msg = db[username]["conversations"][conversation]["conversation_history"]
  if db.get(username, {}).get("conversations", {}).get(
      conversation, {}).get("summary") is None and len(msg) > 1:
    long_res, short_res = summary_of_messages()
    # TODO: Add summeries to database
    db[username]["conversations"][conversation]["summary"] = long_res
    db[username]["conversations"][conversation]["short_summary"] = short_res
    convo = session.get("convo")
    d_base = g.d_base
    d_base.update_conversation_summaries(convo, long_res, short_res)
  messages = []
  for observed_dict in msg.value:
    messages.append(observed_dict.value)
  for message in messages:
    if message["role"] != "system":
      message["content"] = markdown2.markdown(message["content"],
                                              extras=["fenced-code-blocks"])
  # sats code
  sats = session.get("sats")
  # TODO: grab sats from database
  database_sats = db[username]["sats"]
  # TODO: Recently Paid = Database pull
  if sats == None:
    db[username]["sats"] = 0
    session["sats"] = 0
    return render_template("pay.html", username=username)
  elif db[username]["recently_paid"] and database_sats > sats:
    session["sats"] = database_sats
    # TODO: update database with recently paid value
    db[username]["recently_paid"] = False
    sats = database_sats
  elif sats <= 0:
    db[username]["sats"] = 0
    session["sats"] = 0
    return render_template("pay.html", username=username)
  if session.get("force_buy"):
    # TODO: database stuff
    db[username]["sats"] = sats
    session["force_buy"] = False
    return render_template("pay.html", username=username)
  for index, message in enumerate(messages):
    message["index"] = index
  return render_template("chat.html",
                         messages=messages,
                         title=session.get("title"),
                         text=text,
                         token_left=sats)


@app.route("/respond", methods=["POST"])
def respond():
  if not session.get("username"):
    return redirect("/")
  messages = []
  username = session["username"]
  conversation = session["conversation"]
  # TODO: grab messages and conversation history from database
  msg = db[username]["conversations"][conversation]["messages"]
  if db[username]["conversations"][conversation][
      "conversation_history"] is None:
    conversation_history = []
  else:
    conversation_history = db[username]["conversations"][conversation][
      "conversation_history"]
  for observed_dict in msg.value:
    messages.append(observed_dict.value)
    if observed_dict in conversation_history:
      continue
    else:
      conversation_history.append(observed_dict)
  if request.method == 'POST':
    message = request.form.get("message")
    message_estimate = estimate_tokens(message)
    session["message_estimate"] = message_estimate
    previous_token_usage = session.get("token_usage")
    if previous_token_usage != None and message_estimate != None:
      total_tokens = previous_token_usage + message_estimate
      logging.debug(f"Token Estimation: {message_estimate}")
      pre_cost = get_bitcoin_cost(total_tokens)
      if pre_cost > session["sats"]:
        # check to see if cost is likely to exceed balance.
        logging.info(
          f"{pre_cost} sats cost is more than {session['sats']} sats balance")
        session["force_buy"] = True
        return jsonify({"response": ""})
    messages.append({"role": "user", "content": message})
    if not message in conversation_history:
      conversation_history.append({"role": "user", "content": message})
  response, token_usage = res(messages)
  session["token_usage"] = token_usage
  # sats code, getting cost in sats
  cost = get_bitcoin_cost(token_usage)
  sats = session.get("sats") - cost
  session["sats"] = sats
  # TODO: update database with new sats value
  db[username]["sats"] = sats
  if token_usage > TOKEN_LIMIT:
    oldest_assistant_message = next(
      (msg for msg in messages if msg["role"] == "assistant"), None)
    logging.info("Token limit reached. Removing oldest assistant message!")
    if oldest_assistant_message:
      messages.remove(oldest_assistant_message)
  messages.append({"role": "assistant", "content": response})
  if not response in conversation_history:
    conversation_history.append({"role": "assistant", "content": response})
  # TODO: convert database stuff here too
  users = db.prefix("user")
  for user in users:
    if db[user]["username"] == session["username"]:
      db[user]["conversations"][conversation][
        "conversation_history"] = conversation_history
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
  # TODO: More Database updates here
  db[username]["conversations"][conversation]["messages"] = [{
    "role":
    "system",
    "content":
    f"{prompt}"
  }]
  db[username]["conversations"][conversation]["conversation_history"] = [{
    "role":
    "system",
    "content":
    f"{prompt}"
  }]
  db[username]["conversations"][conversation].pop("summary")
  db[username]["conversations"][conversation].pop("short_summary")
  logging.info("summary removed")
  session.pop("prompt", None)
  session.pop("title", None)
  session.pop("conversation", None)
  return redirect(f"/?t={text}")


@app.route("/delete_convo", methods=["GET"])
def delete_convo():
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  conversation = request.args["conversation"]
  # TODO: more database updates here
  users = db.prefix("user")
  for user in users:
    if db[user]["username"] == username:
      del db[username]["conversations"][conversation]
      session.pop("conversation", None)
      break
  return redirect("/")


@app.route("/delete_msg", methods=["GET"])
def delete_msg():
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  conversation = session["conversation"]
  msg_index = int(request.args["msg"])
  # TODO: Figure out how to do delete messages via database update
  length_msg = len(db[username]["conversations"][conversation]["messages"])
  length_con_hist = len(
    db[username]["conversations"][conversation]["conversation_history"])
  difference = length_con_hist - length_msg
  try:
    del db[username]["conversations"][conversation]["conversation_history"][
      msg_index]
    del db[username]["conversations"][conversation]["messages"][msg_index -
                                                                difference]
    return redirect("/chat")
  except Exception as e:
    logging.error(e)
    return redirect("/chat")


def summary_of_messages():
  if not session.get("username"):
    return redirect("/")
  username = session["username"]
  conversation = session["conversation"]
  # TODO: Doing Message Summary Work via Database pull
  messages = db[username]["conversations"][conversation]["messages"]
  summary_msgs = ""
  for index, message in enumerate(messages):
    if message["role"] == "user":
      if index > 1:
        break
      summary_msgs += message["content"]
    elif message["role"] == "assistant":
      pass
  prompt = "The user's question or request should be summerized into seven words or less. No explanation or elaboration. Response needs to be seven words or less, no puncutation."
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
  # TODO: Pull conversation history and messages from database
  messages = db[username]["conversations"][conversation][
    "conversation_history"]
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
  session.pop("sats", None)
  session.pop("token_usage", None)
  return redirect("/")


if __name__ == "__main__":
  socketio.run(app, debug=False, host='0.0.0.0', port=81)
