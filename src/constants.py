import os
from pathlib import Path


TOKEN_LIMIT = 3000
SATS = 0.00000001
GPT4_COST = 0.10
CHATGPT_COST = 0.0099
LNBITS_URL = "https://legend.lnbits.com/api/v1/payments/"
BITCOIN_PRICE_URL = "https://api.kraken.com/0/public/Ticker?pair=xbtusd"
MARKDOWN_DIR = Path("static/markdown/")


DATABASE = "prime_database.db"
PASSPHRASE = os.getenv("DATABASE_PASSPHRASE")
SECRET_KEY = os.getenv("GPT_API")
API_KEY = os.getenv("LNBITS_API")
HEADERS = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}
