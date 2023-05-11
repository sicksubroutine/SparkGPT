import string, random, uuid, hashlib, os, openai, time, requests, logging

logging.basicConfig(filename='logfile.log', level=logging.INFO)

secretKey = os.environ['gpt-API']
openai.api_key = f"{secretKey}"

SATS = 0.00000001


def random_token() -> str:
  ran_token = ''.join(
    random.choice(string.ascii_uppercase + string.digits) for _ in range(16))
  return ran_token


def get_IP_Address(request):
  ip_address = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
  return ip_address


def uuid_func():
  device_id = f"{uuid.uuid1()}"
  return device_id


def hash_func(*args):
  args_str = ''.join(args)
  hash_str = hashlib.sha256(args_str.encode()).hexdigest()
  return hash_str


def prompt_get(prompt) -> str:

  prompt_dict = {
    "prompt4chan": {
      "prompt": os.environ['4chanPrompt'],
      "title": "4Chan AI"
    },
    "IFSPrompt": {
      "prompt": os.environ['IFSPrompt'],
      "title": "IFS AI"
    },
    "KetoPrompt": {
      "prompt": os.environ['KetoPrompt'],
      "title": "Keto AI"
    },
    "PythonPrompt": {
      "prompt": os.environ['PythonPrompt'],
      "title": "Python AI"
    },
    "TherapistPrompt": {
      "prompt": os.environ['TherapistPrompt'],
      "title": "Therapist AI"
    },
    "foodMenuPrompt": {
      "prompt": os.environ['foodMenuPrompt'],
      "title": "Food Menu AI"
    },
    "HelpfulPrompt": {
      "prompt": os.environ['HelpfulPrompt'],
      "title": "General AI"
    },
    "AI_Talks_To_Self": {
      "prompt": os.environ['TalkToSelfPrompt'],
      "title": "Recursive AI"
    },
  }
  return prompt_dict.get(prompt, {
    'prompt': 'Invalid Prompt',
    'title': 'Invalid title'
  })


def check_old_markdown():
  path = "static/markdown/"
  if not os.path.exists(path):
    os.makedirs(path)
  for filename in os.listdir(path):
    if filename.endswith(".md"):
      os.remove(path + filename)


def res(messages, model="gpt-3.5-turbo") -> str:
  retry = True
  retry_count = 0
  max_retries = 5
  backoff_time = 1  # seconds
  assistant_response = ""
  token_usage = 0
  while retry:
    try:
      logging.info("Attempting to send message to assistant...")
      response = openai.ChatCompletion.create(model=model, messages=messages)
      assistant_response = response["choices"][0]["message"]["content"]
      token_usage = response["usage"]["total_tokens"]
      logging.info(response["usage"])
      retry = False
      break
    except openai.error.APIError as e:
      logging.error(f"OpenAI API returned an API Error: {e}")
      retry_count += 1
      if retry_count >= max_retries:
        retry = False
        break
      time.sleep(backoff_time * 2**retry_count)
    except openai.error.APIConnectionError as e:
      logging.error(f"Failed to connect to OpenAI API: {e}")
      retry_count += 1
      if retry_count >= max_retries:
        retry = False
        break
      time.sleep(backoff_time * 2**retry_count)
    except openai.error.RateLimitError as e:
      logging.error(f"OpenAI API request exceeded rate limit: {e}")
      retry_count += 1
      if retry_count >= max_retries:
        retry = False
        break
      time.sleep(backoff_time * 2**retry_count)
  return assistant_response, token_usage


def estimate_tokens(text, method="max"):
  word_count = len(text.split(" "))
  char_count = len(text)
  tokens_count_per_word_est = word_count / 0.6
  tokens_count_char_est = char_count / 4.0
  output = 0
  if method == "average":
    output = (tokens_count_per_word_est + tokens_count_char_est) / 2
  elif method == "words":
    output = tokens_count_per_word_est
  elif method == "chars":
    output = tokens_count_char_est
  elif method == 'max':
    output = max(tokens_count_per_word_est, tokens_count_char_est)
  elif method == 'min':
    output = min(tokens_count_per_word_est, tokens_count_char_est)
  else:
    # return invalid method message
    return "Invalid method. Use 'average', 'words', 'chars', 'max', or 'min'."
  return int(output) + 5


def get_bitcoin_cost(tokens, model="gpt-3.5-turbo"):
  if model == "gpt-3.5-turbo":
    cost = 0.0099  # chatgpt per 1k tokens
  elif model == "gpt-4":
    cost = 0.10  # gpt4 per 1k tokens
  url = "https://api.kraken.com/0/public/Ticker?pair=xbtusd"
  r = requests.get(url)
  data = r.json()["result"]["XXBTZUSD"]["c"]
  return round(((tokens / 1000) * cost / round(float(data[0]))) / SATS)
