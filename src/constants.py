import os

TOKEN_LIMIT = 3000
API_KEY = os.getenv("LNBITS_API")
LNBITS_URL = "https://legend.lnbits.com/api/v1/payments/"
HEADERS = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}
SATS = 0.00000001
SECRETKEY = os.getenv("GPT_API")
