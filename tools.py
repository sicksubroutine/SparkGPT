import string, random

def random_token() -> str:
  return ''.join(
    random.choice(string.ascii_letters + string.digits) for _ in range(30))

def get_IP_Address(request):
  ip_address = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
  return ip_address