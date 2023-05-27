from flask import render_template, session, request, redirect, send_file, jsonify
from flask import Response, g
from flask_socketio import SocketIO
from flask_seasurf import SeaSurf
from tools import DataUtils, ChatUtils, BitcoinUtils
from db_manage import DatabaseManager
from __init__ import app
import os 
import markdown 
import qrcode 
import random 
import logging

logging.basicConfig(filename='logfile.log', level=logging.ERROR)

if os.path.exists(".env"):
  from dotenv import load_dotenv
  load_dotenv()
  logging.debug("Loading .env file.")
else:
  logging.debug("Not loading .env file.")

## TODO: Improve current prompts.
## TODO: Make the chat app look better across different interfaces. Responsive.
## TODO: Consider adding a way to login with the Lightning Network.
## NOTE: LNURL-AUTH : https://github.com/lnurl/luds/blob/luds/04.md
## TODO: Add a way to do streaming messages. (SSE)
## TODO: Encrypt data in the database.

TOKEN_LIMIT = 3000
csrf = SeaSurf()
csrf.init_app(app)
socketio = SocketIO(app)

@app.route("/", methods=["GET"])
def index():
  if session.get("username"):
    return redirect("/conversations")
  text = request.args.get("t")
  return render_template("index.html", text=text)
    

@app.route("/conversations", methods=["GET"])
def conversations():
  if not session.get("username"):
    return redirect("/")
  text = request.args.get("t")
  username = session["username"]
  base:DatabaseManager = g.base
  conv = base.get_conversations_for_user(username)
  users = base.get_all_users()
  logging.info(f"Number of users: {len(users)}")
  return render_template("conv.html", text=text, conversations=conv)

@csrf.include
@app.route("/signup", methods=["GET"])
def signup():
  if session.get("username"):
    return redirect("/")
  text = request.args.get("t")
  return render_template("signup.html", text=text)

@app.route("/signup_function", methods=["POST"])
def signup_function():
  if session.get("username"):
    return redirect("/")
  try:
    username = request.form["username"]
    base = g.base
    user = base.get_user(username)
    if user is not None:
      raise Exception("Username already exists!")
    password = request.form["password"]
    password_confirm = request.form["password_confirm"]
    if password != password_confirm:
      raise Exception("Passwords do not match!")
    salt = DataUtils.saltGet()
    password_hash = DataUtils.hash_func(password, salt)
    user_agent = request.headers['User-Agent']
    uuid = DataUtils.uuid_func()
    ip_address = DataUtils.get_IP_Address(request)
    creation_date = DataUtils.time_get()
    identity_hash = DataUtils.hash_func(
      ip_address, 
      uuid, 
      user_agent
    )
    base.insert_user(
      username=username,
      password=password_hash,
      salt=salt,
      ip_address=ip_address,
      uuid=uuid,
      user_agent=user_agent,
      identity_hash=identity_hash,
      sats=0,
      recently_paid=False,
      creation_date=creation_date
    )
    return redirect("/conversations")
  except Exception as e:
    logging.error(e)
    return redirect(f"/?t={e}")

@csrf.include
@app.route("/login", methods=["GET"])
def login():
  if session.get("username"):
    return redirect("/")
  text = request.args.get("t")
  return render_template("login.html", text=text)  
  
@app.route("/login_function", methods=["POST"])
def login_function():
  if session.get("username"):
    return redirect("/")
  try:
    username = request.form["username"]
    base = g.base
    user = base.get_user(username)
    if user is None:
      raise Exception("User does not exist!")
    password = request.form["password"]
    database_password = user["password"]
    salt = user["salt"]
    password_hash = DataUtils.hash_func(password, salt)
    if password_hash != database_password:
      raise Exception("Incorrect username or password!")
    session["username"] = username
    session["ip_address"] = user["ip_address"]
    session["uuid"] = user["uuid"]
    session["identity_hash"] = user["identity_hash"]
    return redirect("/conversations")
  except Exception as e:
    logging.error(e)
    return redirect(f"/?t={e}")
 
@app.route("/logout")
def logout():
  session.clear()
  return redirect("/")

##### Bitcoin Related #####

@app.route('/get_invoice', methods=['GET'])
def get_invoice():
  try:
    sats = int(request.args["sats"])
    memo = f"Payment for {sats} Sats"
    session.pop("payment_request", None)
    session.pop("payment_hash", None)
    invoice = BitcoinUtils.get_lightning_invoice(sats, memo)
    payment_request = invoice["payment_request"]
    payment_hash = invoice["payment_hash"]
    username = session["username"]
    base:DatabaseManager = g.base
    base.insert_payment(
      username=username,
      amount=sats,
      memo=memo,
      payment_request=payment_request,
      payment_hash=payment_hash,
      invoice_status='not paid'
    )
    session["payment_request"] = payment_request
    session["payment_hash"] = payment_hash
    return {"status": "success", "payment_request": payment_request}
  except Exception as e:
    logging.error(e)
    return {"status": "error"}


@app.route("/qrcode_gen", methods=['GET'])
def qrcode_gen() -> str:
  payment_request = request.args.get('payment_request')
  qr_code = qrcode.make(f"lightning:{payment_request}")
  random_filename = "qrcode_" + str(random.randint(0, 1000000)) + ".png"
  path = (f"static/qr/{random_filename}")
  if not os.path.exists("static/qr/"):
    os.makedirs("static/qr/")
  qr_code.save(f"static/qr/{random_filename}")
  return path


"""
@app.route("/webhook", methods=["POST"])
def webhook():
  data = request.json
  if data is None:
    logging.error("No data received.")
    DataUtils.clean_up_invoices()
    return "OK"
  payment_hash = data.get("payment_hash")
  paid = BitcoinUtils.payment_check(payment_hash)
  if paid:
    base:DatabaseManager = g.base
    base.update_payment(payment_hash, "invoice_status", "paid")
    text = f"{payment_hash} has been paid!"
    logging.info(text)
    payment = base.get_payment(payment_hash)
    sats = payment["amount"]
    username = payment["username"]
    current_user = base.get_user(username)
    current_balance = current_user["sats"]
    current_balance += sats
    base.update_user(username, "sats", current_balance)
    base.update_user(username, "recently_paid", True)
    current_user = base.get_user(username)
    DataUtils.clean_up_invoices()
  return "OK"
  """


@app.route('/payment_updates')
def payment_updates():
  payment_hash = session["payment_hash"]
  base:DatabaseManager = g.base
  #invoice_status = base.get_invoice_status(payment_hash)
  paid = BitcoinUtils.payment_check(payment_hash)
  if paid:
    data = 'data: {"status": "paid"}\n\n'
    base.update_payment(payment_hash, "invoice_status", "paid")
    text = f"{payment_hash} has been paid!"
    logging.info(text)
    payment = base.get_payment(payment_hash)
    sats = payment["amount"]
    username = payment["username"]
    current_user = base.get_user(username)
    current_balance = current_user["sats"]
    current_balance += sats
    base.update_user(username, "sats", current_balance)
    base.update_user(username, "recently_paid", True)
    current_user = base.get_user(username)
    DataUtils.clean_up_invoices()
  else:
    data = 'data: {"status": "not paid"}\n\n'
  return Response(data, content_type='text/event-stream')


@app.route('/top_up')
def top_up():
  if not session.get("username"):
    return redirect("/")
  username = session.get('username')
  return render_template('pay.html', username=username, info="Topping up your balance!")

##########################################################

##### Chat Related #####

@app.route("/custom_prompt", methods=["POST"])
def custom_prompt():
  model = request.form["model"]
  session["custom_prompt"] = request.form["prompt"]
  session["title"] = "Custom Prompt"
  session["prompt"] = "CustomPrompt"
  session["model"] = model
  return redirect("/process?custom_prompt=True")
  
@app.route("/prompt", methods=["POST"])
def prompt():
  model = request.form["model"]
  prompt = request.form["prompt"]
  prompt_dict = ChatUtils.prompt_get(prompt)
  session["title"] = prompt_dict["title"]
  session["prompt"] = prompt
  session["model"] = model
  return redirect("/process?custom_prompt=False")

@app.route("/convo_open", methods=["GET"])
def convo_open():
  base:DatabaseManager = g.base
  convo_id = request.args.get("conversation")
  convo = base.get_conversation(convo_id)
  prompt = convo["prompt"]
  if prompt == "CustomPrompt":
    custom_prompt = True
  else:
    custom_prompt = False
  session["title"] = convo["title"]
  session["prompt"] = convo["prompt"]
  session["model"] = convo["model"]
  session["convo"] = convo_id
  return redirect(f"/process?custom_prompt={custom_prompt}&convo=True")

@csrf.exempt
@app.route('/process', methods=['GET'])
def process():
  if not session.get("username"):
    return redirect("/")
  base:DatabaseManager = g.base
  username = session.get('username')
  ##########################################################
  try:
    if not request.args.get("custom_prompt"):
      raise Exception("Invalid method.")
    model = session["model"]
    prompt = session["prompt"]
    title = session["title"]
    custom_prompt = True if request.args.get("custom_prompt") == "True" else False
    if custom_prompt:
      prompt_text = session["custom_prompt"]
      opening = f'Custom Prompt: {session["custom_prompt"]}'
      session["opening"] = opening
    else:
      prompt_text = ChatUtils.prompt_get(prompt)["prompt"]
      opening = ChatUtils.prompt_get(prompt)["opening"]
      session["opening"] = opening
    if request.args.get("convo"):
      return redirect("/chat")
  except Exception as e:
    logging.debug(f"Unable to login {e}")
    text = f"Unable to login! Error: {e}"
    return redirect(f"/?t={text}")
  ##########################################################
  convo = base.insert_conversation(
    username, 
    model,
    title, 
    prompt, 
    prompt_text
  )
  session["convo"] = convo["conversation_id"]
  return redirect("/chat")

def does_user_have_enough_sats(username:str) -> bool:
  base:DatabaseManager = g.base
  user = base.get_user(username)
  database_sats = user["sats"]
  recently_paid = user["recently_paid"]
  if database_sats <= 99:
    return False
  if recently_paid:
    base.update_user(username, "recently_paid", False)
    return True
  return True
  
def message_over_balance(username:str, message:str, model:str) -> bool:
  base:DatabaseManager = g.base
  sats = base.get_user(username)["sats"] - 99
  message_estimate = ChatUtils.estimate_tokens(message)
  previous_token_usage = session.get("token_usage")
  if previous_token_usage is not None:
    total_tokens = previous_token_usage + message_estimate
    logging.debug(f"Token Estimation: {message_estimate}")
    # check to see if cost is likely to exceed balance.
    pre_cost = BitcoinUtils.get_bitcoin_cost(total_tokens, model)
    if pre_cost > sats:
        logging.info(f"{pre_cost} sats cost is more than {sats} sats balance")
        session["force_buy"] = True
        return True
  return False

@app.route("/chat", methods=["GET"])
def chat():
  if not session.get("username"):
    return redirect("/")
  base:DatabaseManager = g.base
  text = request.args.get("t")
  username = session["username"]
  convo = session["convo"]
  ##########################################################
  msg = base.get_messages(convo)
  more_than_1_msg:bool = len(msg) > 1
  no_summary:bool = len(base.get_conversation_summaries(convo)["summary"]) == 0
  if no_summary and more_than_1_msg:
    long_res, short_res = DataUtils.summary_of_messages(convo)
    base.update_conversation_summaries(
      convo, 
      long_res, 
      short_res
    )
  ##########################################################
  messages = []
  for dict in msg:
    messages.append(dict)
  for message in messages:
    if message["role"] != "system":
      message["content"] = markdown.markdown(
      message["content"], 
      extensions=['fenced_code']
    )
  ##########################################################
  # sats code
  user = base.get_user(username)
  sats = user["sats"]
  if sats is None:
    sats = 0
  if session["force_buy"]:
    session["force_buy"] = False
    return render_template("pay.html", username=username, info="Less than 100 Sats!")
  if not does_user_have_enough_sats(username):
    return render_template("pay.html", username=username, info="Insufficient Sats!")
  else:
    return render_template(
      "chat.html",
      messages=messages,
      title=session.get("title"),
      text=text,
      sats_left=sats,
      model=session.get("model"),
      opening=session.get("opening")
    )  

def message_removal(messages, token_usage, convo) -> None:
  base:DatabaseManager = g.base
  session["token_usage"] = token_usage
  usage_over_limit:bool = token_usage > TOKEN_LIMIT
  if usage_over_limit:
    oldest_assistant_message = next(
      (msg for msg in messages if msg["role"] == "assistant"), None)
    logging.info("Token limit reached. Removing oldest assistant message!")
    if oldest_assistant_message:
      oldest_assistant_message_id = oldest_assistant_message["id"]
      base.delete_message(convo, oldest_assistant_message_id)
  

@app.route("/respond", methods=["POST"])
def respond():
  if not session.get("username"):
    return redirect("/")
  base:DatabaseManager = g.base
  messages = []
  username = session["username"]
  if not does_user_have_enough_sats(username):
    session["force_buy"] = True
    return jsonify({"response": ""})
  ##########################################################
  convo = session["convo"]
  model = session["model"]
  message = request.form["message"]
  if message_over_balance(username, message, model):
    return jsonify({"response": "Message over balance!"})
  msg = base.get_messages(convo)
  for dict in msg:
    messages.append(dict)
  messages = [{
    k: v for k, v in d.items() if k in ['role','content']} 
    for d in messages
  ]
  messages.append({"role": "user", "content": message})
  base.insert_message(
    convo, 
    "user", 
    message
  )
  user_message_id = base.insert_conversation_history(
    convo, 
    "user", 
    message
  )
  user_string = render_template(
    "del_msg.html", 
    message_id=user_message_id
  )
  response, token_usage = ChatUtils.openai_response(messages, model)
  ##########################################################
  cost = BitcoinUtils.get_bitcoin_cost(token_usage, model)
  database_sats = base.get_user(username)["sats"]
  sats = database_sats - cost
  base.update_user(
    username, 
    "sats", 
    sats
  )
  ##########################################################
  message_removal(messages, token_usage, convo)
  base.insert_message(
    convo, 
    "assistant",
    response
  )
  assistant_message_id = base.insert_conversation_history(
    convo, 
    "assistant", 
    response
  )
  assistant_string = render_template(
    "del_msg.html", 
    message_id=assistant_message_id
  )
  response = markdown.markdown(
    response, 
    extensions=['fenced_code']
  )
  return jsonify({
    "response": response,
    "user_string": user_string,
    "assistant_string": assistant_string,
    "sats": sats
  })


@app.route("/reset")
def reset_messages():
  if not session.get("username"):
    return redirect("/")
  convo = session.get("convo")
  base:DatabaseManager = g.base
  base.reset_conversation(convo)
  base.reset_conversation_summaries(convo)
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
  base:DatabaseManager = g.base
  base.delete_conversation(convo)
  return redirect("/")


@app.route("/delete_msg", methods=["GET"])
def delete_msg():
  if not session.get("username"):
    return redirect("/")
  convo = session["convo"]
  msg_id = int(request.args["msg"])
  base:DatabaseManager = g.base
  base.delete_message(
    convo, 
    msg_id
  )
  return redirect("/chat")

@app.route("/export")
def export_messages():
  if not session.get("username"):
    return redirect("/")
  DataUtils.check_old_markdown()
  convo = session["convo"]
  title = session["title"]
  model = session["model"]
  path_filename = DataUtils.export_as_markdown(
    convo, 
    title, 
    model
  )
  return send_file(path_filename, as_attachment=True)

if __name__ == "__main__":
  socketio.run(app, host='0.0.0.0', port=81)
