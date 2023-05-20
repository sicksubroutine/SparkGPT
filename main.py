from flask import render_template, session, request, redirect, send_file,jsonify
from flask import Response, g
from flask_socketio import SocketIO
from tools import DataUtils, ChatUtils, BitcoinUtils
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
## TODO: Create basic auth with username and password or possibly a single string.

TOKEN_LIMIT = 3000
socketio = SocketIO(app)

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


@app.route('/get_invoice', methods=['GET'])
def get_invoice():
  try:
    sats = request.args.get('sats')
    if sats is None:
      raise Exception("No sats provided.")
    memo = f"Payment for {sats} Sats"
    session.pop("payment_request", None)
    session.pop("payment_hash", None)
    invoice = BitcoinUtils.get_lightning_invoice(sats, memo)
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
def qrcode_gen() -> str:
  payment_request = request.args.get('payment_request')
  qr_code = qrcode.make(f"lightning:{payment_request}")
  random_filename = "qrcode_" + str(random.randint(0, 1000000)) + ".png"
  path = (f"static/qr/{random_filename}")
  if not os.path.exists("static/qr/"):
    os.makedirs("static/qr/")
  qr_code.save(f"static/qr/{random_filename}")
  return path


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
    DataUtils.clean_up_invoices()
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


@app.route("/custom_prompt", methods=["POST"])
def custom_prompt():
  model = request.form["model"]
  session["custom_prompt"] = request.form["prompt"]
  session["title"] = "Custom Prompt"
  session["prompt"] = "CustomPrompt"
  session["model"] = model
  return redirect("/login?custom_prompt=True")
  
@app.route("/prompt", methods=["POST"])
def prompt():
  model = request.form["model"]
  prompt = request.form["prompt"]
  prompt_dict = ChatUtils.prompt_get(prompt)
  session["title"] = prompt_dict["title"]
  session["prompt"] = prompt
  session["model"] = model
  return redirect("/login?custom_prompt=False")

@app.route("/convo_open", methods=["GET"])
def convo_open():
  d_base = g.d_base
  convo_id = request.args.get("conversation")
  convo = d_base.get_conversation(convo_id)
  prompt = convo["prompt"]
  if prompt == "CustomPrompt":
    custom_prompt = True
  else:
    custom_prompt = False
  session["title"] = convo["title"]
  session["prompt"] = convo["prompt"]
  session["model"] = convo["model"]
  session["convo"] = convo_id
  return redirect(f"/login?custom_prompt={custom_prompt}&convo=True")


@app.route('/login', methods=['GET'])
def login():
  d_base = g.d_base
  uuid = DataUtils.uuid_func()
  ip_address = DataUtils.get_IP_Address(request)
  user_agent = request.headers.get('User-Agent')
  username = session.get('username')
  identity_hash = DataUtils.hash_func(
    ip_address, 
    uuid, 
    user_agent
  )
  ##########################################################
  try:
    if not request.args.get("custom_prompt"):
      raise Exception("Invalid method.")
    model = session["model"]
    prompt = session["prompt"]
    title = session.get("title")
    custom_prompt = True if request.args.get("custom_prompt") == "True" else False
    if custom_prompt:
      prompt_text = session["custom_prompt"]
    else:
      prompt_text = ChatUtils.prompt_get(prompt)["prompt"]
    if request.args.get("convo"):
      return redirect("/chat")
  except Exception as e:
    logging.debug(f"Unable to login {e}")
    text = f"Unable to login! Error: {e}"
    return redirect(f"/?t={text}")
  ##########################################################
  if username is None:
    username = "user" + DataUtils.random_token()
    session["username"] = username
    session["ip_address"] = ip_address
    session["uuid"] = uuid
    session["identity_hash"] = identity_hash
    d_base.insert_user(
      username, 
      ip_address, 
      uuid, 
      user_agent,
      identity_hash
    )
    convo = d_base.insert_conversation(
      username, 
      model,
      title, 
      prompt, 
      prompt_text
    )
    session["convo"] = convo["conversation_id"]
    return redirect("/chat")
  else:
    convo = d_base.insert_conversation(
      username, 
      model, 
      title,
      prompt, 
      prompt_text
    )
    session["convo"] = convo["conversation_id"]
    return redirect("/chat")


@app.route('/top_up')
def top_up():
  if not session.get("username"):
    return redirect("/")
  username = session.get('username')
  return render_template('pay.html', username=username)

#FIXME: This is a giant mess. Clean it up.
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
    long_res, short_res = DataUtils.summary_of_messages(convo)
    d_base.update_conversation_summaries(convo, long_res, short_res)
  messages = []
  for dict in msg:
    messages.append(dict)
  for message in messages:
    if message["role"] != "system":
      message["content"] = markdown.markdown(
      message["content"], 
      extensions=['fenced_code']
    )
  # sats code
  sats = session.get("sats")
  user = d_base.get_user(username)
  database_sats = user["sats"]
  recently_paid = user["recently_paid"]
  #TODO: Seperate this into a seperate function.
  if sats is None:
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

#FIXME: This is a mess, needs to be cleaned up.
@app.route("/respond", methods=["POST"])
def respond():
  if not session.get("username"):
    return redirect("/")
  messages = []
  username = session["username"]
  convo = session.get("convo")
  model = session.get("model")
  if model is None:
    model = "gpt-3.5-turbo"
  d_base = g.d_base
  sats = d_base.get_user(username)["sats"]
  if sats <= 0:
    session["force_buy"] = True
    return jsonify({"response": ""})
  msg = d_base.get_messages(convo)
  messages = []
  for dict in msg:
    messages.append(dict)
  messages = [{
    k: v for k, v in d.items() if k in ['role','content']} 
    for d in messages
  ]
  if request.method == 'POST':
    message = request.form.get("message")
    if message is None:
      return jsonify({"response": ""})
    message_estimate = ChatUtils.estimate_tokens(message)
    session["message_estimate"] = message_estimate
    previous_token_usage = session.get("token_usage")
    if previous_token_usage is not None and message_estimate is not None:
      total_tokens = previous_token_usage + message_estimate
      logging.debug(f"Token Estimation: {message_estimate}")
      # check to see if cost is likely to exceed balance.
      pre_cost = BitcoinUtils.get_bitcoin_cost(total_tokens, model)
      if pre_cost > sats:
        logging.info(f"{pre_cost} sats cost is more than {sats} sats balance")
        session["force_buy"] = True
        return jsonify({"response": ""})
    messages.append({"role": "user", "content": message})
    d_base.insert_message(convo, "user", message)
    d_base.insert_conversation_history(convo, "user", message)
  response, token_usage = ChatUtils.openai_response(messages, model)
  session["token_usage"] = token_usage
  # sats code, getting cost in sats
  cost = BitcoinUtils.get_bitcoin_cost(token_usage, model)
  session_sats = session.get("sats")
  if session_sats is None:
    return jsonify({"response": ""})
  sats = session_sats - cost
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

@app.route("/export")
def export_messages():
  if not session.get("username"):
    return redirect("/")
  DataUtils.check_old_markdown()
  convo = session["convo"]
  title = session.get("title")
  model = session.get("model")
  path_filename = DataUtils.export_as_markdown(convo, title, model) # type: ignore
  return send_file(path_filename, as_attachment=True)

@app.route("/logout")
def logout():
  session.clear()
  return redirect("/")


if __name__ == "__main__":
  socketio.run(app, host='0.0.0.0', port=81)
