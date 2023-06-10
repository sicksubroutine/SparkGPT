from flask import render_template, session, request, redirect, send_file, jsonify
from flask import Response, g
from flask_socketio import SocketIO
from flask_seasurf import SeaSurf
from various_tools import DataUtils, ChatUtils, BitcoinUtils
from db_manage import DatabaseManager
from __init__ import app, logger, debug_logger
import os 
import markdown 
import qrcode 
import random 
import traceback

## TODO: Improve current prompts.
## TODO: Make the chat app look better across different interfaces. Responsive.
## TODO: Consider adding a way to login with the Lightning Network.
## NOTE: LNURL-AUTH : https://github.com/lnurl/luds/blob/luds/04.md
## TODO: Add a way to do streaming messages. (SSE)

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
    username = request.form["username"].lower()
    base:DatabaseManager = g.base
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
    text = "Account created! Please login!"
    return redirect(f"/login?t={text}")
  except Exception as e:
    logger.error(e)
    return redirect(f"/?t={e}")

@csrf.include
@app.route("/login", methods=["GET"])
def login():
  try:
    if session.get("username"):
      return redirect("/")
    text = request.args.get("t")
    return render_template("login.html", text=text)
  except Exception as e:
    trace = traceback.format_exc()
    logger.error(f"Failed to login: {e}")
    debug_logger.debug(f"Failed to login: {trace}")
    return render_template("error.html", error=e, trace=trace)
  
@app.route("/login_function", methods=["POST"])
def login_function():
  if session.get("username"):
    return redirect("/")
  try:
    username = request.form["username"].lower()
    base:DatabaseManager = g.base
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
    session["force_buy"] = False
    session["identity_hash"] = user["identity_hash"]
    base.update_user(username, "last_login", DataUtils.time_get())
    if user["admin"]:
      session["admin"] = True
    else:
      session["admin"] = False
    return redirect("/conversations")
  except Exception as e:
    trace = traceback.format_exc()
    logger.error(f"Failed to login: {e}")
    debug_logger.debug(f"Failed to login: {trace}")
    return redirect(f"/login?t={e}")
  
  
@app.route("/admin_panel", methods=["GET"])
def admin_panel():
  if not session.get("username") and not session["admin"]:
    return redirect("/")
  username = session["username"]
  text = request.args.get("t")
  base:DatabaseManager = g.base
  users = base.get_user_info()
  return render_template("panel.html", users=users, text=text, username=username)

@app.route("/update_sats", methods=["POST"])
def update_sats():
  if not session.get("username") and not session["admin"]:
    return redirect("/")
  sats = request.form["sats"]
  username = request.form["username"]
  base:DatabaseManager = g.base
  base.update_user(username, "sats", sats)
  return redirect(f"/admin_panel?t=Sats updated to {sats} for {username}!")
  
  
 
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
    trace = traceback.format_exc()
    logger.error(f"Failed to get invoice: {e}")
    debug_logger.debug(f"Failed to get invoice: {trace}")
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
    logger.info(text)
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

@app.route("/conversations", methods=["GET"])
def conversations():
  try:
    if not session.get("username"):
      return redirect("/")
    base:DatabaseManager = g.base
    text = request.args.get("t")
    username = session["username"]
    user = base.get_user(username)
    conv = base.get_conversations_for_user(username)
    return render_template(
      "conv.html", 
      text=text, 
      conversations=conv, 
      admin=user["admin"]
    )
  except Exception as e:
    trace = traceback.format_exc()
    logger.error(f"Failed to load conversations: {e}")
    debug_logger.debug(f"Failed to load conversations: {trace}")
    return render_template("error.html", error=e, trace=trace)

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
  username = session['username']
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
    trace = traceback.format_exc()
    logger.error(f"Unable to process process data: {e}")
    debug_logger.debug(f"Unable to process process data: {trace}")
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
    debug_logger.debug(f"Token Estimation: {message_estimate}")
    # check to see if cost is likely to exceed balance.
    pre_cost = BitcoinUtils.get_bitcoin_cost(total_tokens, model)
    if pre_cost > sats:
        logger.info(f"{pre_cost} sats cost is more than {sats} sats balance")
        session["force_buy"] = True
        return True
  return False

@app.route("/chat", methods=["GET"])
def chat():
  try:
    if not session.get("username"):
      return redirect("/")
    base:DatabaseManager = g.base
    text = request.args.get("t")
    username = session["username"]
    convo = session["convo"]
    msg = base.get_messages(convo)
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
  except Exception as e:
    trace = traceback.format_exc()
    logger.error(f"Unable to load chat page: {e}")
    debug_logger.debug(f"Unable to load chat page: {trace}")
    return render_template("error.html", error=e, trace=trace)
  
def message_removal(token_usage, convo) -> None:
  base:DatabaseManager = g.base
  usage_over_limit:bool = token_usage > TOKEN_LIMIT
  if usage_over_limit:
    message = base.delete_oldest_message(convo)
    if message is None:
      return
    debug_logger.debug("Token limit reached. Removing oldest assistant message!")
    debug_logger.debug(f"Removed message: {message}")
    messages = base.get_messages(convo)
    message_contents = []
    for dict in messages: 
      message_contents.append(dict["role"])
      message_contents.append(dict["content"])
    token_usage = ChatUtils.estimate_tokens(" ".join(message_contents))
    debug_logger.debug(f"New token usage: {token_usage}")
    if not token_usage:
      token_usage = 0
    usage_over_limit:bool = token_usage > TOKEN_LIMIT
    if usage_over_limit:
      message_removal(token_usage, convo)
    

@app.route("/respond", methods=["POST"])
def respond():
  if not session.get("username"):
    return redirect("/")
  base:DatabaseManager = g.base
  over_balance = False
  messages = []
  username = session["username"]
  if not does_user_have_enough_sats(username):
    session["force_buy"] = True
    return jsonify({
      "over_balance": over_balance, 
      "response": ""
    })
  ##########################################################
  convo = session["convo"]
  model = session["model"]
  message = request.form["message"]
  if message_over_balance(username, message, model):
    over_balance = True
    return jsonify({
      "over_balance": over_balance,
      "response": ""
    })
  msg = base.get_messages(convo)
  no_summary:bool = len(base.get_conversation_summaries(convo)["summary"]) == 0
  if no_summary:
    long_res, short_res = DataUtils.summary_of_messages(message)
    base.update_conversation_summaries(
      convo, 
      long_res, 
      short_res
    )
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
  user_del_msg = render_template(
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
  message_removal(token_usage, convo)
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
  assistant_del_msg = render_template(
    "del_msg.html", 
    message_id=assistant_message_id
  )
  response = markdown.markdown(
    response, 
    extensions=['fenced_code']
  )
  return jsonify({
    "response": response,
    "user_string": user_del_msg,
    "assistant_string": assistant_del_msg,
    "sats": sats,
    "over_balance": over_balance
  })


@app.route("/reset")
def reset_messages():
  if not session.get("username"):
    return redirect("/")
  convo = session.get("convo")
  base:DatabaseManager = g.base
  base.reset_conversation(convo)
  base.reset_conversation_summaries(convo)
  logger.info("summary reset")
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
  base.delete_conversation_history(
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
