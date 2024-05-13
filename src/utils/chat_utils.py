from constants import OPENAI_API_KEY
import os
from logging import Logger
import logging
import openai
from typing import Tuple

logger: Logger = logging.getLogger(__name__)

openai.api_key = f"{OPENAI_API_KEY}"


def prompt_get(chosen_prompt: str) -> dict:
    """
    Retrieves a prompt and its associated title based on the given prompt key.

    Args:
        prompt (str): The prompt key used to retrieve the corresponding prompt and title.

    Returns:
        dict: A dictionary containing the prompt and title.
    """
    match chosen_prompt:
        case "prompt4chan":
            prompt = os.environ["4CHANPROMPT"]
            title = "4Chan Green Text"
            opening = "Welcome to Green Text. What's your boggle?"
        case "IFSPrompt":
            prompt = os.environ["IFSPROMPT"]
            title = "Internal Family Systems AI"
            opening = "Welcome to IFS AI. How are you feeling today?"
        case "KetoPrompt":
            prompt = os.environ["KETOPROMPT"]
            title = "Keto Helper"
            opening = "Welcome to the Keto Helper. Do you have any Keto questions?"
        case "CodingBuddy":
            prompt = os.environ["CODINGBUDDYPROMPT"]
            title = "Coding Buddy"
            opening = "Hello! I'm your Coding Buddy. What are you working on today?"
        case "TherapistPrompt":
            prompt = os.environ["THERAPISTPROMPT"]
            title = "Therapist Bot"
            opening = "Welcome to Therapist Bot. What's on your mind today?"
        case "foodMenuPrompt":
            prompt = os.environ["FOODMENUPROMPT"]
            title = "Menu Assistant 8000"
            opening = "Welcome to Menu Assistant 8000. Do you want to create a breakfast, lunch, or dinner menu?"  # noqa
        case "HelpfulPrompt":
            prompt = os.environ["HELPFULPROMPT"]
            title = "General AI"
            opening = "Hello! I'm a Generally Helpful AI. How can I help you?"
        case "AI_Talks_To_Self":
            prompt = os.environ["TALKTOSELFPROMPT"]
            title = "Recursive AI"
        case "CustomPrompt":
            prompt = ""
            title = "Custom Prompt"
        case _:
            prompt = "Invalid Prompt"
            title = "Invalid Title"
            opening = "Invalid Opening"
    return {"prompt": prompt, "title": title, "opening": opening}


def openai_response(messages: list, model: str = "gpt-3.5-turbo") -> Tuple[str, int]:
    """
    Sends messages to the OpenAI assistant and retrieves the assistant's response.

    Args:
        messages (list): A list of message objects representing the conversation history.
        model (str): The OpenAI model to use for generating the response.
        (default: "gpt-3.5-turbo")

    Returns:
        tuple: A tuple containing the assistant's response and token usage.
        The tuple has the following structure: (assistant_response, token_usage)

    Raises:
        openai.error.APIError: If the OpenAI API returns an error.
        openai.error.APIConnectionError: If a connection error occurs
        while communicating with the OpenAI API.
        openai.error.RateLimitError: If the API request exceeds the rate limit.
    """
    try:
        logger.debug("Attempting to send message to assistant...")
        response = openai.ChatCompletion.create(model=model, messages=messages)
        assistant_response = response["choices"][0]["message"]["content"]
        token_usage = response["usage"]["total_tokens"]
        logger.debug(response["usage"])
        return assistant_response, token_usage
    except openai.error.APIError as e:
        logger.error(f"OpenAI API returned an API Error: {e}")
        return None
    except openai.error.APIConnectionError as e:
        logger.error(f"Failed to connect to OpenAI API: {e}")
        return None
    except openai.error.RateLimitError as e:
        logger.error(f"OpenAI API request exceeded rate limit: {e}")
        return None


def estimate_tokens(text: str, method: str = "max") -> int | None:
    """
    Estimates the number of tokens required to process the given text.

    Args:
        text (str): The input text to estimate the tokens for.
        method (str): The method to use for estimating the tokens. (default: "max")
                    Supported methods: 'average', 'words', 'chars', 'max', 'min'

    Returns:
        int: The estimated number of tokens required to process the text.
    """
    word_count = len(text.split())
    char_count = len(text)
    tokens_count_per_word_est = word_count / 0.6
    tokens_count_char_est = char_count / 4.0
    methods = {
        "average": lambda a, b: (a + b) / 2,
        "words": lambda a, b: a,
        "chars": lambda a, b: b,
        "max": max,
        "min": min,
    }
    if method not in methods:
        logger.error("Invalid method.")
        return None
    output = methods[method](tokens_count_per_word_est, tokens_count_char_est)
    return int(output) + 5
