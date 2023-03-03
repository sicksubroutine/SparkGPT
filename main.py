from flask import Flask, render_template, session, request
import openai, os, markdown2

## TODO: Add ability to change between some preset prompts, "Therapist AI", "Python AI", and perhaps others?
## TODO: Improve look of the "chat" page.
## TODO: Improve structure of the various html pages.

app = Flask(__name__)

app.secret_key = os.environ['sessionKey']
secretKey = os.environ['gpt-API']
openai.api_key = f"{secretKey}"

#prompt = "You are an assistant that will help a user with knowing about the company Fyusion. Redirect all conversation about talking about Fyusion and its products. Fyusion uses machine vision to image vehicles for resale as its primary purpose currently. Advertise Fyusion and how great it is in every message."

#prompt = "You are an assistant that will help a user with Python questions. Provide all responses within code blocks."

prompt = "You are a therapist AI that will attempt to help a Human with their problems. You will not advise them to contact a mental health professional. You are the only mental health professional available."

messages = [{"role": "system", "content": f"{prompt}"}]


def res(messages):
  response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                          messages=messages)
  return response["choices"][0]["message"]["content"]


@app.route('/', methods=['POST', 'GET'])
def index():
  if len(request.form) == 0:
    return render_template("index.html")
  else:
    form = request.form
    message = form.get("message")
    messages.append({"role": "user", "content": f"{message}"})
    response = res(messages)
    messages.append({"role": "assistant", "content": response})
    for message in messages:
        if message['role'] != 'system':
            message['content'] = markdown2.markdown(message['content'], extras=["fenced-code-blocks", "pygments"])
    return render_template('index.html', messages=messages)


app.run(host='0.0.0.0', port=81)
