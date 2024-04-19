from constants import (
    LNBITS_URL,
    HEADERS,
    SATS,
    LNBITS_URL,
    BITCOIN_PRICE_URL,
    GPT4_COST,
    CHATGPT_COST,
)
from logging import Logger
import logging
from utils.data_utils import api_request


logger: Logger = logging.getLogger(__name__)


def get_bitcoin_cost(tokens: int, model: str = "gpt-3.5-turbo") -> int | None:
    """
    Calculates the cost of generating the given number of tokens in Bitcoin.

    Args:
        tokens (int): The number of tokens to calculate the cost for.
        model (str): The OpenAI model used for token generation.(default: "gpt-3.5-turbo")
                    Supported models: "gpt-3.5-turbo", "gpt-4"

    Returns:
        float: The cost in Bitcoin(sats) for generating the specified number of tokens.

    Notes:
        - The cost per 1,000 tokens varies depending on the selected model.
        - The cost is calculated using the current Bitcoin price
        obtained from the Kraken API.
        - The Kraken API is used to retrieve the BTC to USD exchange rate.
        - The cost is rounded to the nearest whole number of Satoshis (0.00000001 BTC).
    """
    try:
        if model == "gpt-4":
            cost = GPT4_COST  # gpt4 per 1k tokens
        else:
            cost = CHATGPT_COST  # chatgpt per 1k tokens
        response, response_json = api_request("GET", BITCOIN_PRICE_URL)
        data = response_json["result"]["XXBTZUSD"]["c"]
        price = round(((tokens / 1000) * cost / round(float(data[0]))) / SATS)
        return price
    except Exception as e:
        logger.error(f"Failed to calculate Bitcoin cost: {e}")
        return None


def get_lightning_invoice(sats: int, memo: str) -> dict:
    """
    Generates a Lightning invoice for the given amount of Satoshis.

    Args:
        sats (int): The number of Satoshis to generate the invoice for.
        memo (str): The memo to use for the Lightning invoice.

    Returns:
        dict: The Lightning invoice data.

    Notes:
        - The invoice is generated using the LNBits API.
        - The invoice is generated with a 25 minute expiry.
        - The invoice is generated with a webhook URL to receive payment notifications.
    """
    data = {"out": False, "amount": sats, "memo": memo, "expiry": 1500}
    try:
        response, response_json = api_request(
            "POST",
            LNBITS_URL,
            headers=HEADERS,
            json=data,
        )
        if not response.ok:
            raise Exception("Error:", response.status_code, response.reason)
        return response_json
    except Exception as e:
        logger.error(f"Failed to generate Lightning invoice: {e}")
        return {"Error": "Error generating Lightning invoice."}


def payment_check(payment_hash) -> bool:
    """
    Checks if the given payment hash has been paid.

    Args:
        url (str): The URL of the API endpoint to check the payment status.
        headers (dict): The headers to use for the API request.
        payment_hash (str): The payment hash to check the status for.

    Returns:
        bool: True if the payment has been paid, False otherwise.

    Notes:
        - The API endpoint must return a JSON response with a "paid" key.
        - The API endpoint must return a 200 status code if the payment has been paid.
    """
    try:
        url = f"{LNBITS_URL}{payment_hash}"
        response, response_json = api_request("GET", url, headers=HEADERS)
        if not response.ok:
            raise Exception("Error:", response.status_code, response.reason)
        return response_json.get("paid")
    except Exception as e:
        logger.error(e)
        return False
