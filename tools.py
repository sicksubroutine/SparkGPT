import string, random, uuid, hashlib, os, openai, time

secretKey = os.environ['gpt-API']
openai.api_key = f"{secretKey}"

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
      "title": "Internal Family Systems AI"
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

def res(messages) -> str:
  retry = True
  retry_count = 0
  max_retries = 5
  backoff_time = 1  # seconds
  assistant_response = ""
  token_usage = 0
  while retry:
    try:
      response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
      assistant_response = response["choices"][0]["message"]["content"]
      token_usage = response["usage"]["total_tokens"]
      retry = False
      break
    except openai.error.APIError as e:
      print(f"OpenAI API returned an API Error: {e}")
      retry_count += 1
      if retry_count >= max_retries:
          retry = False
          break
      time.sleep(backoff_time * 2 ** retry_count)
    except openai.error.APIConnectionError as e:
      print(f"Failed to connect to OpenAI API: {e}")
      retry_count += 1
      if retry_count >= max_retries:
          retry = False
          break
      time.sleep(backoff_time * 2 ** retry_count)
    except openai.error.RateLimitError as e:
      print(f"OpenAI API request exceeded rate limit: {e}")
      retry_count += 1
      if retry_count >= max_retries:
          retry = False
          break
      time.sleep(backoff_time * 2 ** retry_count)
  return assistant_response, token_usage
  