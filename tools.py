import string, random, uuid, hashlib, os


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
    "foodMenu": {
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
  for filename in os.listdir(path):
    if filename.endswith(".md"):
      os.remove(path + filename)
