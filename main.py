from flask import Flask, render_template, session, request, redirect, send_file, jsonify, Response, g
from flask_socketio import SocketIO
import os, markdown, requests, qrcode, random, logging, sqlite3
from tools import random_token, get_IP_Address, uuid_func, hash_func, prompt_get, check_old_markdown, res, get_bitcoin_cost, estimate_tokens
from db_manage import DatabaseManager

logging.basicConfig(filename='logfile.log', level=logging.error)

## TODO: Add more prompts.
## TODO: Make the front page look better.
## TODO: Make the chat app look better across different interfaces. Responsive.
## TODO: Consider adding a way to login with the Lightning Network.
## LNURL-AUTH : https://github.com/lnurl/luds/blob/luds/04.md
## TODO: Add ability to change AI models, partially complete.

API_KEY = os.environ['LNBITS_API']
URL = "https://legend.lnbits.com/api/v1/payments/"
HEADERS = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}
TOKEN_LIMIT = 3000

app = Flask(__name__, static_url_path='/static')
app.secret_key = os.environ['SESSIONKEY']
socketio = SocketIO(app)

DATABASE = "prime_database.db"


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
    d_base = g.d_base
    conv = d_base.get_conversations_for_user(username)
    users = d_base.get_all_users()
    logging.info(f"Number of users: {len(users)}")
  return render_template("index.html", text=text, conversations=conv)


"""def run_out_of_sats(message=None):
  d_base = g.d_base
  username = session["username"]
  user = d_base.get_user(username)
  database_sats = user["sats"]
  if not message:
    if database_sats <= 0:
      return True
  previous_token_usage = session.get("token_usage")
  message_estimate = estimate_tokens(message)
  return False"""


def clean_up_invoices():
  path = "static/qr/"
  for filename in os.listdir(path):
    if filename.endswith(".png"):
      os.remove(path + filename)


@app.route('/get_invoice', methods=['GET'])
def get_invoice():
  try:
    sats = request.args.get('sats')
    memo = f"Payment for {sats} Sats"
    data = {
      "out": False,
      "amount": sats,
      "memo": memo,
      "expiry": 1500,
      "webhook": "https://chatgpt-flask-app.thechaz.repl.co/webhook"
    }
    res = requests.post(URL, headers=HEADERS, json=data)
    if not res.ok:
      raise Exception("Error:", res.status_code, res.reason)
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
  except Exception as e:
    logging.error(e)
    return {"status": "error"}


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
  try:
    url = f"{URL}{payment_hash}"
    response = requests.get(url, headers=HEADERS)
    response_json = response.json()
    if not response.ok:
      raise Exception("Error:", response.status_code, response.reason)
    return response_json.get("paid")
  except Exception as e:
    logging.error(e)


@app.route("/webhook", methods=["POST"])
def webhook():
  data = request.json
  payment_hash = data.get("payment_hash")
  paid = payment_check(payment_hash)
  if paid:
    d_base = g.d_base
    d_base.update_payment(payment_hash, "invoice_status", "paid")
    text = f"{payment_hash} has been paid!"
    logging.info(text)
    payment = d_base.get_payment(payment_hash)
    sats = payment["amount"]
    username = payment["username"]
    current_user = d_base.get_user(username)
    current_balance = current_user["sats"]
    current_balance += sats
    d_base.update_user(username, "sats", current_balance)
    d_base.update_user(username, "recently_paid", True)
    current_user = d_base.get_user(username)
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
      prompt = request.form.get("prompt")
      model = request.form.get("model")
      prompt_dict = prompt_get(prompt)
      chosen_prompt = prompt_dict["prompt"]
      title = prompt_dict["title"]
      session["title"] = title
      session["prompt"] = prompt
      session["model"] = model
    elif 'custom_prompt' in request.form:
      prompt = "CustomPrompt"
      chosen_prompt = request.form.get('custom_prompt')
      title = "Custom Prompt"
      session["title"] = title
      session["prompt"] = chosen_prompt
  elif 'conversation' in request.args:
    convo_id = request.args.get('conversation')
    session["convo"] = convo_id
    d_base = g.d_base
    convo = d_base.get_conversation(convo_id)
    prompt = convo["prompt"]
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
      d_base = g.d_base
      users = d_base.get_all_users()
      for user in users:
        if identity_hash == user["identity_hash"]:
          session["username"] = user["username"]
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
        d_base = g.d_base
        d_base.insert_user(username, ip_address, uuid, user_agent,
                           identity_hash)
        user = d_base.get_user(username)
        convo = d_base.insert_conversation(username, prompt, chosen_prompt)
        session["convo"] = convo["conversation_id"]
        return redirect("/chat")
    else:
      if session.get("username") and session.get("identity_hash"):
        d_base = g.d_base
        convo = d_base.insert_conversation(username, prompt, chosen_prompt)
        session["convo"] = convo["conversation_id"]
      return redirect("/chat")


@app.route('/top_up')
def top_up():
  if not session.get("username"):
    return redirect("/")
  username = session.get('username')
  return render_template('pay.html', username=username)


@app.route("/chat", methods=["GET"])
def chat():
  if not session.get("username"):
    return redirect("/")
  text = request.args.get("t")
  username = session["username"]
  convo = session["convo"]
  d_base = g.d_base
  msg = d_base.get_messages(convo)
  summary = d_base.get_conversation_summaries(convo)["summary"]
  if len(summary) == 0 and len(msg) > 1:
    long_res, short_res = summary_of_messages()
    convo = session.get("convo")
    d_base.update_conversation_summaries(convo, long_res, short_res)
  messages = []
  for dict in msg:
    messages.append(dict)
  for message in messages:
    if message["role"] != "system":
      message["content"] = markdown.markdown(message["content"],
                                             extensions=['fenced_code'])
  # sats code
  sats = session.get("sats")
  user = d_base.get_user(username)
  database_sats = user["sats"]
  recently_paid = user["recently_paid"]
  if sats == None:
    d_base.update_user(username, "sats", 0)
    session["sats"] = 0
    return render_template("pay.html", username=username)
  elif recently_paid and database_sats > sats:
    session["sats"] = database_sats
    d_base.update_user(username, "recently_paid", False)
    sats = database_sats
  elif sats <= 0:
    d_base.update_user(username, "sats", 0)
    session["sats"] = 0
    return render_template("pay.html", username=username)
  if session.get("force_buy"):
    d_base.update_user(username, "sats", sats)
    session["force_buy"] = False
    return render_template("pay.html", username=username)
  return render_template("chat.html",
                         messages=messages,
                         title=session.get("title"),
                         text=text,
                         token_left=sats,
                         model=session.get("model"))


@app.route("/respond", methods=["POST"])
def respond():
  if not session.get("username"):
    return redirect("/")
  messages = []
  username = session["username"]
  convo = session.get("convo")
  model = session.get("model")
  d_base = g.d_base
  msg = d_base.get_messages(convo)
  messages = []
  for dict in msg:
    messages.append(dict)
  messages = [{k: v
               for k, v in d.items() if k in ['role', 'content']}
              for d in messages]
  if request.method == 'POST':
    message = request.form.get("message")
    message_estimate = estimate_tokens(message)
    session["message_estimate"] = message_estimate
    previous_token_usage = session.get("token_usage")
    if previous_token_usage != None and message_estimate != None:
      total_tokens = previous_token_usage + message_estimate
      logging.debug(f"Token Estimation: {message_estimate}")
      pre_cost = get_bitcoin_cost(total_tokens, model)
      sats = d_base.get_user(username)["sats"]
      if pre_cost > sats:
        # check to see if cost is likely to exceed balance.
        logging.info(f"{pre_cost} sats cost is more than {sats} sats balance")
        session["force_buy"] = True
        return jsonify({"response": ""})
    messages.append({"role": "user", "content": message})
    d_base.insert_message(convo, "user", message)
    d_base.insert_conversation_history(convo, "user", message)
  response, token_usage = res(messages, model)
  session["token_usage"] = token_usage
  # sats code, getting cost in sats
  cost = get_bitcoin_cost(token_usage, model)
  sats = session.get("sats") - cost
  session["sats"] = sats
  d_base.update_user(username, "sats", sats)
  if token_usage > TOKEN_LIMIT:
    oldest_assistant_message = next(
      (msg for msg in messages if msg["role"] == "assistant"), None)
    logging.info("Token limit reached. Removing oldest assistant message!")
    if oldest_assistant_message:
      oldest_assistant_message_id = oldest_assistant_message["id"]
      d_base.delete_message(convo, oldest_assistant_message_id)
  d_base.insert_message(convo, "assistant", response)
  d_base.insert_conversation_history(convo, "assistant", response)
  return jsonify({"response": response})


@app.route("/reset")
def reset_messages():
  if not session.get("username"):
    return redirect("/")
  convo = session.get("convo")
  d_base = g.d_base
  d_base.reset_conversation(convo)
  d_base.reset_conversation_summaries(convo)
  logging.info("summary reset")
  session.pop("prompt", None)
  session.pop("title", None)
  session.pop("convo", None)
  text = "Chat Reset!"
  return redirect(f"/?t={text}")


@app.route("/delete_convo", methods=["GET"])
def delete_convo():
  if not session.get("username"):
    return redirect("/")
  convo = request.args["conversation"]
  d_base = g.d_base
  d_base.delete_conversation(convo)
  return redirect("/")


@app.route("/delete_msg", methods=["GET"])
def delete_msg():
  if not session.get("username"):
    return redirect("/")
  convo = session["convo"]
  msg_id = int(request.args["msg"])
  d_base = g.d_base
  d_base.delete_message(convo, msg_id)
  return redirect("/chat")


def summary_of_messages():
  if not session.get("username"):
    return redirect("/")
  convo = session["convo"]
  d_base = g.d_base
  messages = d_base.get_messages(convo)
  summary_msgs = ""
  for index, message in enumerate(messages):
    if message["role"] == "user":
      if index > 1:
        break
      summary_msgs += message["content"]
    elif message["role"] == "assistant":
      pass
  prompt = "The user's question or request should be summarized into seven words or less. No explanation or elaboration. Response needs to be seven words or less, no punctuation."
  arr = [{
    "role": "system",
    "content": f"{prompt}"
  }, {
    "role": "user",
    "content": summary_msgs
  }]
  response, _ = res(arr)
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
  convo = session["convo"]
  d_base = g.d_base
  messages = d_base.get_conversation_history(convo)
  summary = d_base.get_conversation_summaries(convo)["short_summary"]
  markdown = ""
  for message in messages:
    if message['role'] == 'system':
      markdown += session.get("title") + "\n\n"
      markdown += session.get("model") + "\n\n"
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
  session.clear()
  return redirect("/")


if __name__ == "__main__":
  socketio.run(app, debug=False, host='0.0.0.0', port=81)
